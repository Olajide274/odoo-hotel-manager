from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestBookingSlug(TransactionCase):

    def _hotel(self, name):
        co = self.env['res.company'].create({'name': name})
        rt = self.env['hotel.room.type'].create({
            'name': 'T', 'price_per_night': 1000, 'company_id': co.id})
        self.env['hotel.room'].create({
            'name': name[:3], 'room_type_id': rt.id, 'company_id': co.id})
        return co

    def test_slugs_are_unique(self):
        a = self._hotel('Slug Hotel')
        b = self._hotel('Slug-Hotel')
        self.assertTrue(a.hotel_booking_slug)
        self.assertNotEqual(a.hotel_booking_slug, b.hotel_booking_slug)

    def test_public_rooms_only_from_own_hotel(self):
        a = self._hotel('Alpha Inn')
        b = self._hotel('Beta Inn')
        self.assertEqual(a._hotel_public_rooms().mapped('company_id'), a)
        self.assertNotIn(b._hotel_public_rooms(), a._hotel_public_rooms())
