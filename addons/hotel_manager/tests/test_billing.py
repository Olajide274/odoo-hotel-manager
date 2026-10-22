from odoo.exceptions import UserError, ValidationError
from odoo.tests import tagged
from odoo.tests.common import TransactionCase, new_test_user


@tagged('post_install', '-at_install')
class TestHotelBilling(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        company = cls.env.company
        # Minimal accounting data so the tests work with or without a chart.
        cls.receivable = cls.env['account.account'].create({
            'name': 'Hotel Test Receivable', 'code': 'HT1100',
            'account_type': 'asset_receivable',
            'company_ids': [(6, 0, company.ids)],
        })
        cls.income = cls.env['account.account'].create({
            'name': 'Hotel Test Income', 'code': 'HT4000',
            'account_type': 'income',
            'company_ids': [(6, 0, company.ids)],
        })
        journal = cls.env['account.journal'].search([
            ('type', '=', 'sale'), ('company_id', '=', company.id)], limit=1)
        if not journal:
            cls.env['account.journal'].create({
                'name': 'Hotel Test Sales', 'code': 'HTS', 'type': 'sale',
                'default_account_id': cls.income.id,
            })
        cls.partner = cls.env['res.partner'].create({'name': 'Billing Guest'})
        cls.partner.property_account_receivable_id = cls.receivable

        room_type = cls.env['hotel.room.type'].create({
            'name': 'Billing Standard', 'price_per_night': 25000,
        })
        cls.room = cls.env['hotel.room'].create({
            'name': 'BL101', 'room_type_id': room_type.id,
        })
        cls.receptionist = new_test_user(
            cls.env, login='hm_recep3',
            groups='base.group_user,hotel_manager.group_hotel_receptionist')

    def _booking(self, check_in_now=True, **extra):
        vals = {
            'guest_name': 'Billing Guest',
            'partner_id': self.partner.id,
            'room_id': self.room.id,
            'check_in': '2026-12-01',
            'check_out': '2026-12-04',    # 3 nights x 25,000 = 75,000
        }
        vals.update(extra)
        booking = self.env['hotel.booking'].create(vals)
        if check_in_now:
            booking.action_confirm()
            booking.action_check_in()
        return booking

    def _charge(self, booking, description, quantity, unit_price, category='bar'):
        return self.env['hotel.booking.charge'].create({
            'booking_id': booking.id, 'description': description,
            'quantity': quantity, 'unit_price': unit_price, 'category': category,
        })

    def test_folio_and_invoice_totals_match(self):
        booking = self._booking()
        self._charge(booking, 'Beer', 2, 3500)                     # 7,000
        self._charge(booking, 'Shirts', 3, 1000, 'laundry')        # 3,000
        self.assertEqual(booking.charges_total, 10000)
        self.assertEqual(booking.folio_total, 85000)
        booking.action_create_invoice()
        invoice = booking.invoice_id
        self.assertEqual(invoice.move_type, 'out_invoice')
        self.assertEqual(invoice.partner_id, self.partner)
        self.assertEqual(len(invoice.invoice_line_ids), 3)
        self.assertEqual(invoice.amount_total, booking.folio_total)

    def test_invoice_with_no_extra_charges(self):
        booking = self._booking()
        booking.action_create_invoice()
        self.assertEqual(booking.invoice_id.amount_total, 75000)

    def test_invoice_requires_checked_in(self):
        booking = self._booking(check_in_now=False)
        with self.assertRaises(UserError):
            booking.action_create_invoice()
        booking.action_confirm()
        with self.assertRaises(UserError):
            booking.action_create_invoice()

    def test_cannot_invoice_twice(self):
        booking = self._booking()
        booking.action_create_invoice()
        with self.assertRaises(UserError):
            booking.action_create_invoice()

    def test_charges_locked_after_invoice(self):
        booking = self._booking()
        charge = self._charge(booking, 'Beer', 1, 3500)
        booking.action_create_invoice()
        with self.assertRaises(UserError):
            charge.unit_price = 1
        with self.assertRaises(UserError):
            charge.unlink()
        with self.assertRaises(UserError):
            self._charge(booking, 'Late beer', 1, 3500)

    def test_cancelled_invoice_allows_recreate(self):
        booking = self._booking()
        self._charge(booking, 'Beer', 1, 3500)
        booking.action_create_invoice()
        first = booking.invoice_id
        first.button_cancel()
        self.assertFalse(booking.has_live_invoice)
        self._charge(booking, 'Water', 1, 500)
        booking.action_create_invoice()
        self.assertNotEqual(booking.invoice_id, first)
        self.assertEqual(booking.invoice_id.amount_total, 79000)

    def test_charges_need_checked_in_booking(self):
        booking = self._booking(check_in_now=False)
        with self.assertRaises(UserError):
            self._charge(booking, 'Beer', 1, 3500)

    def test_charge_validation(self):
        booking = self._booking()
        with self.assertRaises(ValidationError):
            self._charge(booking, 'Nothing', 0, 3500)
        with self.assertRaises(ValidationError):
            self._charge(booking, 'Negative', 1, -5)

    def test_new_invoice_is_unpaid(self):
        booking = self._booking()
        self.assertFalse(booking.payment_state)
        booking.action_create_invoice()
        self.assertEqual(booking.payment_state, 'not_paid')

    def test_receptionist_can_bill(self):
        booking = self._booking()
        self.env['hotel.booking.charge'].with_user(self.receptionist).create({
            'booking_id': booking.id, 'description': 'Jollof rice',
            'quantity': 2, 'unit_price': 4000, 'category': 'food',
        })
        booking.with_user(self.receptionist).action_create_invoice()
        self.assertEqual(booking.invoice_id.amount_total, 83000)

    def test_guest_contact_reused_by_email(self):
        first = self._booking(
            partner_id=False, guest_name='Ada Obi', guest_email='ada@example.com')
        partner = first._get_invoice_partner()
        self.assertEqual(partner.email, 'ada@example.com')
        second = self._booking(
            check_in_now=False, partner_id=False, guest_name='Ada O.',
            guest_email='ADA@example.com', check_in='2026-12-10', check_out='2026-12-12')
        self.assertEqual(second._get_invoice_partner(), partner)

