from datetime import timedelta

from odoo import fields
from odoo.addons.hotel_manager.controllers.verify import (
    check_disposable, check_password)
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestSignupVerification(TransactionCase):

    def setUp(self):
        super().setUp()
        self.company = self.env['res.company'].create({'name': 'Verify Hotel'})
        self.user = self.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'V', 'login': 'verify@test.com', 'email': 'verify@test.com',
            'password': 'S0me-strong-pass', 'active': False,
            'company_id': self.company.id, 'company_ids': [(6, 0, [self.company.id])],
        })
        self.Token = self.env['hotel.signup.token']

    def _login_lookup(self):
        return self.env['res.users'].search([('login', '=', 'verify@test.com')])

    def test_unverified_user_cannot_log_in_but_verified_can(self):
        self.assertFalse(self._login_lookup())
        raw, problem = self.Token.issue(self.user)
        self.assertIsNone(problem)
        self.assertTrue(self.Token.consume(raw))
        self.assertTrue(self._login_lookup())

    def test_token_is_single_use(self):
        raw, _ = self.Token.issue(self.user)
        self.assertTrue(self.Token.consume(raw))
        self.assertIsNone(self.Token.consume(raw))

    def test_expired_token_rejected(self):
        raw, _ = self.Token.issue(self.user)
        self.Token.search([('user_id', '=', self.user.id)]).expires_at = (
            fields.Datetime.now() - timedelta(hours=1))
        self.assertIsNone(self.Token.consume(raw))
        self.assertFalse(self._login_lookup())

    def test_unknown_token_rejected(self):
        self.assertIsNone(self.Token.consume('not-a-real-token'))

    def test_resend_is_rate_limited(self):
        raw, _ = self.Token.issue(self.user)
        self.assertTrue(raw)
        raw2, problem = self.Token.issue(self.user)
        self.assertIsNone(raw2)
        self.assertEqual(problem, 'wait')

    def test_new_token_revokes_old_one(self):
        raw, _ = self.Token.issue(self.user)
        self.env.cr.execute(
            "UPDATE hotel_signup_token SET create_date = create_date - interval '5 minutes' "
            "WHERE user_id = %s", (self.user.id,))
        self.Token.invalidate_model()
        raw2, _ = self.Token.issue(self.user)
        self.assertIsNone(self.Token.consume(raw))
        self.assertTrue(self.Token.consume(raw2))

    def test_password_rules(self):
        for bad in ('short', 'password123', '1234567890', 'verify@test.com'):
            with self.assertRaises(UserError):
                check_password(bad, 'verify@test.com')
        check_password('strong-pass-9', 'verify@test.com')

    def test_disposable_domain_blocked(self):
        with self.assertRaises(UserError):
            check_disposable('someone@mailinator.com')
        check_disposable('someone@gmail.com')
