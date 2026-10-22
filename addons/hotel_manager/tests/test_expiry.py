from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests.common import TransactionCase


class TestSubscriptionExpiry(TransactionCase):

    def setUp(self):
        super().setUp()
        Plan = self.env['hotel.plan']
        self.free = Plan.search([('code', '=', 'free')], limit=1)
        self.paid = Plan.search([('code', '=', 'standard')], limit=1)
        self.company = self.env['res.company'].create(
            {'name': 'Expiry Test Hotel', 'hotel_plan_id': self.free.id})

    def test_state_transitions(self):
        today = fields.Date.context_today(self.company)
        self.assertEqual(self.company.hotel_subscription_state, 'trial')
        self.company.trial_end_date = today - timedelta(days=1)
        self.assertEqual(self.company.hotel_subscription_state, 'expired')
        self.assertEqual(self.company.hotel_subscription_notification()['params']['type'], 'danger')
        self.company.hotel_plan_id = self.paid
        self.assertEqual(self.company.hotel_subscription_state, 'active')

    def test_expired_blocks_booking(self):
        self.company.trial_end_date = fields.Date.context_today(self.company) - timedelta(days=1)
        with self.assertRaises(UserError):
            self.env['hotel.booking'].create({'company_id': self.company.id})
