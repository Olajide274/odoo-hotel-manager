import hashlib
import hmac
import json
import logging
from odoo import http, fields
from odoo.http import request

_logger = logging.getLogger(__name__)


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
            # Fallback: just confirm the draft booking if Paystack is not configured
            booking.action_confirm()
            return request.redirect('/hotel/book?success=1&ref=%s' % booking.name)

        amount_kobo = int(booking.total_price * 100)  # Paystack expects kobo

        payload = {
            'email': booking.guest_email,
            'amount': amount_kobo,
            'currency': 'NGN',
            'reference': booking.name,
            'callback_url': f'{base_url}/hotel/book/callback',
            'metadata': {
                'booking_id': booking.id,
                'guest_name': booking.guest_name,
            },
        }

        # In real use you would call Paystack initialize API here.
        # For the addon we store the intent and let the frontend or a simple redirect handle it.
        # For simplicity in this phase we confirm on webhook only.
        booking.message_post(body="Paystack payment initiated.")
        return request.redirect(
            f'https://checkout.paystack.com/{public_key}'  # placeholder – real flow uses initialize API
        )

    @http.route('/hotel/book/webhook', type='json', auth='public', methods=['POST'], csrf=False)
    def paystack_webhook(self, **kwargs):
        """Paystack webhook – must verify signature."""
        payload = request.httprequest.get_data()
        signature = request.httprequest.headers.get('x-paystack-signature', '')

        ICP = request.env['ir.config_parameter'].sudo()
        secret = ICP.get_param('hotel_manager.paystack_secret_key') or ''

        computed = hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha512
        ).hexdigest()

        if not hmac.compare_digest(computed, signature):
            _logger.warning("Paystack webhook: invalid signature")
            return {'status': 'invalid signature'}

        try:
            data = json.loads(payload)
        except Exception:
            return {'status': 'bad json'}

        event = data.get('event')
        if event != 'charge.success':
            return {'status': 'ignored'}

        reference = data.get('data', {}).get('reference')
        if not reference:
            return {'status': 'no reference'}

        booking = request.env['hotel.booking'].sudo().search([
            ('name', '=', reference),
            ('state', '=', 'draft'),
        ], limit=1)

        if not booking:
            _logger.warning("Paystack webhook: booking %s not found or not draft", reference)
            return {'status': 'booking not found'}

        # Confirm booking + create invoice/payment (re-use existing billing methods)
        booking.action_confirm()
        if hasattr(booking, 'action_create_invoice'):
            booking.action_create_invoice()
        if hasattr(booking, 'action_register_payment'):
            booking.action_register_payment()

        booking.message_post(body="Payment confirmed via Paystack webhook.")
        _logger.info("Paystack webhook: booking %s confirmed", booking.name)
        return {'status': 'ok'}

    @http.route('/hotel/book/callback', type='http', auth='public', website=True)
    def paystack_callback(self, **kwargs):
        """Guest returns here after Paystack checkout."""
        reference = kwargs.get('reference') or kwargs.get('trxref')
        if reference:
            booking = request.env['hotel.booking'].sudo().search([
                ('name', '=', reference)
            ], limit=1)
            if booking and booking.state in ('confirmed', 'checked_in'):
                return request.redirect('/hotel/book?success=1&ref=%s' % booking.name)
        return request.redirect('/hotel/book?error=payment_pending')
