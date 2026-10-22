from psycopg2 import IntegrityError

from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user
from odoo.tools import mute_logger


@tagged('post_install', '-at_install')
class TestHotelRoom(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.room_type = cls.env['hotel.room.type'].create({
            'name': 'Deluxe', 'price_per_night': 50000, 'capacity': 2,
        })
        cls.room = cls.env['hotel.room'].create({
            'name': 'T101', 'room_type_id': cls.room_type.id,
        })
        cls.manager = new_test_user(
            cls.env, login='hm_manager',
            groups='base.group_user,hotel_manager.group_hotel_manager')
        cls.receptionist = new_test_user(
            cls.env, login='hm_recep',
            groups='base.group_user,hotel_manager.group_hotel_receptionist')

    def test_price_defaults_from_room_type(self):
        self.assertEqual(self.room.price_per_night, 50000)
        self.assertEqual(self.room.status, 'available')

    def test_room_count_on_type(self):
        self.assertEqual(self.room_type.room_count, 1)

    def test_duplicate_room_name_rejected(self):
        with self.assertRaises(IntegrityError), mute_logger('odoo.sql_db'):
            self.env['hotel.room'].create({
                'name': 'T101', 'room_type_id': self.room_type.id,
            })

    def test_negative_price_rejected(self):
        with self.assertRaises(ValidationError):
            self.room.price_per_night = -1

    def test_receptionist_can_read_and_update_status(self):
        room = self.room.with_user(self.receptionist)
        self.assertEqual(room.name, 'T101')
        room.status = 'occupied'
        self.assertEqual(self.room.status, 'occupied')

    def test_receptionist_cannot_create_room_or_edit_type(self):
        with self.assertRaises(AccessError):
            self.env['hotel.room'].with_user(self.receptionist).create({
                'name': 'T102', 'room_type_id': self.room_type.id,
            })
        with self.assertRaises(AccessError):
            self.room_type.with_user(self.receptionist).name = 'Hacked'

    def test_manager_can_create_everything(self):
        rtype = self.env['hotel.room.type'].with_user(self.manager).create({
            'name': 'Suite', 'price_per_night': 120000,
        })
        room = self.env['hotel.room'].with_user(self.manager).create({
            'name': 'T201', 'room_type_id': rtype.id,
        })
        self.assertEqual(room.price_per_night, 120000)
