from datetime import timedelta

from odoo import fields
from odoo.exceptions import UserError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestCompanyLicense(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.free = cls.env.ref('hotel_manager.plan_free')
        cls.standard = cls.env.ref('hotel_manager.plan_standard')
        cls.License = cls.env['hotel.license']

    def _hotel(self, name, plan=None):
        vals = {'name': name}
        if plan:
            vals['hotel_plan_id'] = plan.id
        return self.env['res.company'].create(vals)

    def _room(self, company, name):
        rt = self.env['hotel.room.type'].search([('company_id', '=', company.id)], limit=1)
        if not rt:
            rt = self.env['hotel.room.type'].create({
                'name': 'T', 'price_per_night': 1000, 'company_id': company.id})
        return self.env['hotel.room'].create({
            'name': name, 'room_type_id': rt.id, 'company_id': company.id})

    def test_trial_is_three_days(self):
        company = self._hotel('Trial A', self.free)
        today = fields.Date.context_today(company)
        self.assertEqual(company.trial_end_date, today + timedelta(days=3))
        lic = self.License._current(company)
        self.assertEqual(lic.package, 'trial')
        self.assertEqual(lic.status, 'active')

    def test_room_limit_is_per_hotel(self):
        a = self._hotel('Rooms A', self.free)
        b = self._hotel('Rooms B', self.free)
        for i in range(5):
            self._room(a, str(i))
        with self.assertRaises(UserError):
            self._room(a, 'extra')
        self._room(b, '1')

    def test_company_without_plan_is_unrestricted(self):
        company = self._hotel('No plan')
        for i in range(7):
            self._room(company, str(i))

    def test_expired_licence_blocks_new_bookings(self):
        company = self._hotel('Expired', self.free)
        room = self._room(company, '1')
        self.License._current(company).expires_at = (
            fields.Datetime.now() - timedelta(days=1))
        with self.assertRaises(UserError):
            self.env['hotel.booking'].create({
                'guest_name': 'G', 'room_id': room.id, 'company_id': company.id})

    def test_manual_activation_sets_plan_and_licence(self):
        company = self._hotel('Manual', self.free)
        self.assertFalse(self.License.has_feature('billing', company))
        self.env['hotel.plan.activate'].create({
            'company_id': company.id, 'plan_id': self.standard.id,
            'days': 30, 'note': 'bank transfer'}).action_activate()
        today = fields.Date.context_today(company)
        self.assertEqual(company.hotel_plan_id, self.standard)
        self.assertEqual(company.hotel_paid_until, today + timedelta(days=30))
        lic = self.License._current(company)
        self.assertEqual(lic.package, 'pro')
        self.assertEqual(lic.status, 'active')
        self.assertTrue(self.License.has_feature('billing', company))
        self.assertEqual(
            self.env['hotel.plan.activation'].search_count([('company_id', '=', company.id)]), 1)
