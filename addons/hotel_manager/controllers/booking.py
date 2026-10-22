import hashlib
import hmac
import json
import logging
import re
import uuid

import requests
from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)


def _booking_id(reference):
    m = re.match(r'^BK-(\d+)-[0-9a-f]{8}$', reference or '')
    return int(m.group(1)) if m else 0


class HotelBookingController(http.Controller):

    @http.route('/hotel/book', type='http', auth='public', website=True, sitemap=True)
    def booking_form(self, **kwargs):
        rooms = request.env['hotel.room'].sudo().search([
            ('status', '=', 'available'),
            ('active', '=', True),
            ('company_id', '=', request.website.company_id.id),
        ])
        return request.render('hotel_manager.booking_form_template', {
            'rooms': rooms,
            'error': kwargs.get('error'),
            'success': kwargs.get('success'),
        })

    @http.route('/hotel/book/submit', type='http', auth='public', website=True, methods=['POST'], csrf=True)
    def booking_submit(self, **post):
        try:
            room_id = int(post.get('room_id', 0))
            guest_name = (post.get('guest_name') or '').strip()
            guest_email = (post.get('guest_email') or '').strip()
            guest_phone = (post.get('guest_phone') or '').strip()
            check_in = post.get('check_in')
            check_out = post.get('check_out')

            if not all([room_id, guest_name, guest_email, check_in, check_out]):
                return request.redirect('/hotel/book?error=missing_fields')

            room = request.env['hotel.room'].sudo().browse(room_id)
            if not room.exists() or room.status != 'available':
                return request.redirect('/hotel/book?error=room_unavailable')

            Booking = request.env['hotel.booking'].sudo()
            booking = Booking.create({
                'guest_name': guest_name,
                'guest_email': guest_email,
                'guest_phone': guest_phone,
                'room_id': room.id,
                'company_id': room.company_id.id,
                'check_in': check_in,
                'check_out': check_out,
                'state': 'draft',
            })

            # Prepare Paystack payment
            return self._redirect_to_paystack(booking)

        except Exception as e:
            _logger.exception("Public booking failed")
            return request.redirect('/hotel/book?error=server_error')

    def _redirect_to_paystack(self, booking):
        """Create a Paystack transaction and redirect the guest."""
        ICP = request.env['ir.config_parameter'].sudo()
        secret_key = ICP.get_param('hotel_manager.paystack_secret_key')
        public_key = ICP.get_param('hotel_manager.paystack_public_key')
        base_url = ICP.get_param('web.base.url').rstrip('/')

        if not secret_key or not public_key:
            if ICP.get_param('hotel_manager.allow_unpaid_booking') != 'True':
                return request.redirect('/hotel/book?error=payment_unavailable')
            booking.action_confirm()
            return request.redirect('/hotel/book?success=1&ref=%s' % booking.name)

        amount_kobo = round(booking.total_price * 100)  # Paystack expects kobo
        reference = 'BK-%d-%s' % (booking.id, uuid.uuid4().hex[:8])

        payload = {
            'email': booking.guest_email,
            'amount': amount_kobo,
            'currency': 'NGN',
            'reference': reference,
            'callback_url': f'{base_url}/hotel/book/callback',
            'metadata': {
                'booking_id': booking.id,
                'guest_name': booking.guest_name,
            },
        }

        try:
            resp = requests.post(
                'https://api.paystack.co/transaction/initialize', json=payload,
                headers={'Authorization': 'Bearer %s' % secret_key}, timeout=15)
            body = resp.json()
            auth_url = (body.get('data') or {}).get('authorization_url') if body.get('status') else None
        except Exception:
            _logger.exception('Paystack initialize failed')
            auth_url = None
        if not auth_url:
            return request.redirect('/hotel/book?error=payment_unavailable')
        booking.message_post(body='Paystack payment initiated (%s).' % reference)
        return request.redirect(auth_url, local=False)


    @http.route('/hotel/book/callback', type='http', auth='public', website=True)
    def paystack_callback(self, **kwargs):
        """Guest returns here after Paystack checkout."""
        reference = kwargs.get('reference') or kwargs.get('trxref')
        if reference:
            booking = request.env['hotel.booking'].sudo().browse(_booking_id(reference)).exists()
            if booking and booking.state in ('confirmed', 'checked_in'):
                return request.redirect('/hotel/book?success=1&ref=%s' % booking.name)
        return request.redirect('/hotel/book?error=payment_pending')
