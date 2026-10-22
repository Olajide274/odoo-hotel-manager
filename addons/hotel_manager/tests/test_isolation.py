from datetime import timedelta

from odoo import fields
from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestHotelIsolation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        free = cls.env.ref('hotel_manager.plan_free')
        manager = cls.env.ref('hotel_manager.group_hotel_manager')
        internal = cls.env.ref('base.group_user')
        today = fields.Date.today()

        def make_hotel(label):
            company = cls.env['res.company'].create({'name': 'Hotel ' + label, 'hotel_plan_id': free.id})
            user = cls.env['res.users'].with_context(no_reset_password=True).create({
                'name': 'Mgr ' + label, 'login': 'mgr_%s@iso.test' % label.lower(),
                'email': 'mgr_%s@iso.test' % label.lower(),
                'company_id': company.id, 'company_ids': [(6, 0, [company.id])],
                'groups_id': [(6, 0, [internal.id, manager.id])],
            })
            rtype = cls.env['hotel.room.type'].create({
                'name': 'Type ' + label, 'price_per_night': 1000, 'company_id': company.id})
            room = cls.env['hotel.room'].create({
                'name': '1' + label, 'room_type_id': rtype.id, 'company_id': company.id})
            booking = cls.env['hotel.booking'].create({
                'guest_name': 'Guest ' + label, 'room_id': room.id, 'company_id': company.id,
                'check_in': today + timedelta(days=1), 'check_out': today + timedelta(days=2)})
            return company, user, rtype, room, booking

        cls.co_a, cls.user_a, cls.type_a, cls.room_a, cls.book_a = make_hotel('A')
        cls.co_b, cls.user_b, cls.type_b, cls.room_b, cls.book_b = make_hotel('B')

    def _assert_isolated(self, model, own, other):
        found = self.env[model].with_user(self.user_a).search([])
        self.assertIn(own, found)
        self.assertNotIn(other, found)
        with self.assertRaises(AccessError):
            other.with_user(self.user_a).read(['id'])

    def test_rooms(self):
        self._assert_isolated('hotel.room', self.room_a, self.room_b)

    def test_room_types(self):
        self._assert_isolated('hotel.room.type', self.type_a, self.type_b)

    def test_bookings(self):
        self._assert_isolated('hotel.booking', self.book_a, self.book_b)

    def test_manager_cannot_edit_plans(self):
        plan = self.env.ref('hotel_manager.plan_standard')
        with self.assertRaises(AccessError):
            plan.with_user(self.user_a).write({'price_monthly': 1})
