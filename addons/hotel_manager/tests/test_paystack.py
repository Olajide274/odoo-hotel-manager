import hashlib
import hmac
import json

from odoo.tests import HttpCase, tagged


@tagged('post_install', '-at_install')
class TestPaystackWebhook(HttpCase):

    def setUp(self):
        super().setUp()
        self.secret = 'sk_test_unit'
        self.env['ir.config_parameter'].sudo().set_param('hotel_manager.paystack_secret_key', self.secret)
        self.plan = self.env['hotel.plan'].search([('code', '=', 'standard')], limit=1)
        self.company = self.env['res.company'].create({'name': 'Pay Test Hotel'})
        self.pay = self.env['hotel.subscription.payment'].create({
            'company_id': self.company.id, 'plan_id': self.plan.id,
            'reference': 'SUB-T-1', 'amount': 50000.0})

    def _post(self, amount=5000000, secret=None, sig=None):
        raw = json.dumps({'event': 'charge.success', 'data': {
            'reference': 'SUB-T-1', 'amount': amount, 'currency': 'NGN', 'status': 'success'}}).encode()
        sig = sig or hmac.new((secret or self.secret).encode(), raw, hashlib.sha512).hexdigest()
        return self.url_open('/hotel/book/webhook', data=raw,
                             headers={'x-paystack-signature': sig, 'Content-Type': 'application/json'})

    def _refresh(self):
        self.env.invalidate_all()

    def test_bad_signature_rejected(self):
        self.assertEqual(self._post(sig='bad').status_code, 401)
        self._refresh()
        self.assertEqual(self.pay.state, 'pending')

    def test_missing_secret_rejected(self):
        self.env['ir.config_parameter'].sudo().set_param('hotel_manager.paystack_secret_key', '')
        self.assertEqual(self._post(secret='').status_code, 503)

    def test_amount_mismatch_rejected(self):
        self._post(amount=100)
        self._refresh()
        self.assertEqual(self.pay.state, 'pending')
        self.assertFalse(self.company.hotel_plan_id)

    def test_success_activates_and_replay_is_idempotent(self):
        self.assertEqual(self._post().status_code, 200)
        self._refresh()
        self.assertEqual(self.pay.state, 'paid')
        self.assertEqual(self.company.hotel_plan_id, self.plan)
        paid_until = self.company.hotel_paid_until
        self.assertTrue(paid_until)
        self._post()
        self._refresh()
        self.assertEqual(self.company.hotel_paid_until, paid_until)
