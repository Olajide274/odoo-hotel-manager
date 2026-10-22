from odoo.exceptions import AccessError, UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user


@tagged('post_install', '-at_install')
class TestHotelBooking(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.room_type = cls.env['hotel.room.type'].create({
            'name': 'Test Standard', 'price_per_night': 25000,
        })
        cls.room = cls.env['hotel.room'].create({
            'name': 'B101', 'room_type_id': cls.room_type.id,
        })
        cls.room2 = cls.env['hotel.room'].create({
            'name': 'B102', 'room_type_id': cls.room_type.id,
        })
        cls.receptionist = new_test_user(
            cls.env, login='hm_recep2',
            groups='base.group_user,hotel_manager.group_hotel_receptionist')

    def _book(self, check_in, check_out, room=None, **extra):
        vals = {
            'guest_name': 'Test Guest',
            'room_id': (room or self.room).id,
            'check_in': check_in,
            'check_out': check_out,
        }
        vals.update(extra)
        return self.env['hotel.booking'].create(vals)

    def test_nights_and_total(self):
        booking = self._book('2026-11-01', '2026-11-04')
        self.assertEqual(booking.nights, 3)
        self.assertEqual(booking.price_per_night, 25000)
        self.assertEqual(booking.total_price, 75000)

    def test_price_is_snapshot_of_room_price(self):
        booking = self._book('2026-11-01', '2026-11-04')
        self.env.flush_all()
        self.room.price_per_night = 40000
        self.assertEqual(booking.price_per_night, 25000)
        self.assertEqual(booking.total_price, 75000)

    def test_checkout_must_be_after_checkin(self):
        with self.assertRaises(ValidationError):
            self._book('2026-11-04', '2026-11-04')
        with self.assertRaises(ValidationError):
            self._book('2026-11-05', '2026-11-01')

    def test_overlap_rejected(self):
        self._book('2026-11-01', '2026-11-04')
        with self.assertRaises(ValidationError):
            self._book('2026-11-03', '2026-11-06')   # overlaps the end
        with self.assertRaises(ValidationError):
            self._book('2026-10-30', '2026-11-02')   # overlaps the start
        with self.assertRaises(ValidationError):
            self._book('2026-11-02', '2026-11-03')   # inside
        with self.assertRaises(ValidationError):
            self._book('2026-10-30', '2026-11-10')   # surrounds

    def test_back_to_back_allowed(self):
        self._book('2026-11-01', '2026-11-04')
        after = self._book('2026-11-04', '2026-11-06')
        before = self._book('2026-10-30', '2026-11-01')
        self.assertEqual(after.state, 'draft')
        self.assertEqual(before.state, 'draft')

    def test_other_room_same_dates_allowed(self):
        self._book('2026-11-01', '2026-11-04')
        other = self._book('2026-11-01', '2026-11-04', room=self.room2)
        self.assertTrue(other.id)

    def test_cancelled_booking_frees_room(self):
        first = self._book('2026-11-01', '2026-11-04')
        first.action_cancel()
        second = self._book('2026-11-03', '2026-11-06')
        self.assertTrue(second.id)
        with self.assertRaises(ValidationError):
            first.action_reset_draft()

    def test_state_flow(self):
        booking = self._book('2026-11-01', '2026-11-04')
        self.assertEqual(booking.state, 'draft')
        booking.action_confirm()
        self.assertEqual(booking.state, 'confirmed')
        booking.action_check_in()
        self.assertEqual(booking.state, 'checked_in')
        self.assertEqual(self.room.status, 'occupied')
        booking.action_check_out()
        self.assertEqual(booking.state, 'checked_out')
        self.assertEqual(self.room.status, 'cleaning')

    def test_invalid_transitions(self):
        booking = self._book('2026-11-01', '2026-11-04')
        with self.assertRaises(UserError):
            booking.action_check_in()
        with self.assertRaises(UserError):
            booking.action_check_out()
        booking.action_cancel()
        with self.assertRaises(UserError):
            booking.action_confirm()
        with self.assertRaises(UserError):
            booking.action_check_in()

    def test_cannot_check_into_occupied_or_maintenance_room(self):
        booking = self._book('2026-11-01', '2026-11-04')
        booking.action_confirm()
        self.room.status = 'occupied'
        with self.assertRaises(UserError):
            booking.action_check_in()
        self.room.status = 'maintenance'
        with self.assertRaises(UserError):
            booking.action_check_in()

    def test_receptionist_permissions(self):
        booking = self.env['hotel.booking'].with_user(self.receptionist).create({
            'guest_name': 'Walk-in',
            'room_id': self.room.id,
            'check_in': '2026-11-01',
            'check_out': '2026-11-03',
        })
        booking.action_confirm()
        booking.action_check_in()
        self.assertEqual(self.room.status, 'occupied')
        with self.assertRaises(AccessError):
            booking.unlink()

    def test_reference_sequence(self):
        booking = self._book('2026-11-01', '2026-11-04')
        self.assertTrue(booking.name.startswith('BK'))

