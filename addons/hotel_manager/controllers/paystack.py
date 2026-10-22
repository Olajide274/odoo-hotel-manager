import hashlib
import hmac
import json
import logging

from werkzeug.wrappers import Response

from odoo import http
from odoo.http import request

from .booking import _booking_id

_logger = logging.getLogger(__name__)


def _reply(msg, status=200):
    return Response(msg, status=status, content_type='text/plain')


class PaystackWebhook(http.Controller):

    @http.route('/hotel/book/webhook', type='http', auth='public', methods=['POST'], csrf=False)
    def webhook(self, **kw):
        raw = request.httprequest.get_data()
        sig = request.httprequest.headers.get('x-paystack-signature', '')
        secret = request.env['ir.config_parameter'].sudo().get_param('hotel_manager.paystack_secret_key') or ''
        if not secret:
            return _reply('not configured', 503)
        computed = hmac.new(secret.encode(), raw, hashlib.sha512).hexdigest()
        if not hmac.compare_digest(computed.encode(), sig.encode()):
            _logger.warning('Paystack webhook: invalid signature')
            return _reply('invalid signature', 401)
        try:
            payload = json.loads(raw)
        except ValueError:
            return _reply('bad json', 400)
        if payload.get('event') != 'charge.success':
            return _reply('ignored')
        data = payload.get('data') or {}
        ref = data.get('reference') or ''
        env = request.env
        if ref.startswith('SUB-'):
            pay = env['hotel.subscription.payment'].sudo().search([('reference', '=', ref)], limit=1)
            if not pay:
                return _reply('unknown reference')
            return _reply('ok' if pay._confirm_paystack(data) else 'rejected')
        booking = env['hotel.booking'].sudo().browse(_booking_id(ref)).exists()
        if not booking or booking.state != 'draft':
            return _reply('ignored')
        if data.get('currency') != 'NGN' or int(data.get('amount') or 0) != round(booking.total_price * 100):
            _logger.warning('Paystack webhook: amount mismatch for %s', ref)
            return _reply('amount mismatch')
        booking.action_confirm()
        if hasattr(booking, 'action_create_invoice'):
            booking.action_create_invoice()
        if hasattr(booking, 'action_register_payment'):
            booking.action_register_payment()
        booking.message_post(body='Payment confirmed via Paystack webhook (%s).' % ref)
        return _reply('ok')
