from odoo.exceptions import AccessError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestHotelIsolation(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        manager = cls.env.ref('hotel_manager.group_hotel_manager')
        internal = cls.env.ref('base.group_user')
        cls.co_a = cls.env['res.company'].create({'name': 'Iso Hotel A'})
        cls.co_b = cls.env['res.company'].create({'name': 'Iso Hotel B'})
        cls.user_a = cls.env['res.users'].with_context(no_reset_password=True).create({
            'name': 'A', 'login': 'iso_a@test.com', 'email': 'iso_a@test.com',
            'company_id': cls.co_a.id, 'company_ids': [(6, 0, [cls.co_a.id])],
            'groups_id': [(6, 0, [internal.id, manager.id])]})
        rt = cls.env['hotel.room.type'].create({
            'name': 'Iso', 'price_per_night': 1000, 'company_id': cls.co_b.id})
        cls.room_b = cls.env['hotel.room'].create({
            'name': 'B1', 'room_type_id': rt.id, 'company_id': cls.co_b.id})
        cls.booking_b = cls.env['hotel.booking'].create({
            'guest_name': 'Guest B', 'room_id': cls.room_b.id,
            'company_id': cls.co_b.id})

    def test_cannot_see_other_hotel(self):
        for model, rec in (('hotel.room', self.room_b),
                           ('hotel.booking', self.booking_b)):
            seen = self.env[model].with_user(self.user_a).search([('id', '=', rec.id)])
            self.assertFalse(seen, "%s leaks across hotels" % model)

    def test_cannot_edit_other_hotel(self):
        with self.assertRaises(AccessError):
            self.room_b.with_user(self.user_a).write({'status': 'maintenance'})

    def test_dashboard_only_counts_own_hotel(self):
        data = self.env['hotel.dashboard'].with_user(self.user_a).get_data()
        self.assertEqual(data['rooms_total'], 0)
