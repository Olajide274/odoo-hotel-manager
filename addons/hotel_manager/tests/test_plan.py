from datetime import timedelta

from odoo import fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestHotelPlan(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.plan = cls.env['hotel.plan'].create({
            'name': 'Tiny', 'code': 'starter', 'max_rooms': 2,
        }) if not cls.env['hotel.plan'].search([('code', '=', 'starter')]) else \
            cls.env.ref('hotel_manager.plan_starter')
        cls.plan.max_rooms = 2
        cls.company = cls.env['res.company'].create({
            'name': 'Test Hotel', 'hotel_plan_id': cls.plan.id})
        cls.room_type = cls.env['hotel.room.type'].create({
            'name': 'T', 'price_per_night': 1000})

    def _room(self, name):
        return self.env['hotel.room'].create({
            'name': name, 'room_type_id': self.room_type.id,
            'company_id': self.company.id})

    def test_room_limit_blocks_extra_room(self):
        self._room('1')
        self._room('2')
        with self.assertRaises(ValidationError):
            self._room('3')

    def test_unlimited_plan_has_no_limit(self):
        self.plan.max_rooms = 0
        for i in range(5):
            self._room(str(i))

    def test_free_plan_sets_trial_end_date(self):
        free = self.env.ref('hotel_manager.plan_free')
        company = self.env['res.company'].create({
            'name': 'Trial Hotel', 'hotel_plan_id': free.id})
        today = fields.Date.context_today(company)
        self.assertEqual(company.trial_end_date, today + timedelta(days=free.trial_days))
        self.assertTrue(company.is_trial_active)

    def test_expired_trial(self):
        free = self.env.ref('hotel_manager.plan_free')
        company = self.env['res.company'].create({
            'name': 'Old Trial', 'hotel_plan_id': free.id})
        company.trial_end_date = fields.Date.context_today(company) - timedelta(days=1)
        self.assertTrue(company._hotel_trial_expired())
