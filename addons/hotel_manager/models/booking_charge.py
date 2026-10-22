from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError


class HotelBookingCharge(models.Model):
    _name = 'hotel.booking.charge'
    _description = 'Hotel Booking Extra Charge'
    _order = 'date, id'

    booking_id = fields.Many2one(
        'hotel.booking', required=True, ondelete='cascade', index=True)
    date = fields.Date(required=True, default=fields.Date.context_today)
    category = fields.Selection([
        ('bar', 'Bar'),
        ('food', 'Food'),
        ('laundry', 'Laundry'),
        ('other', 'Other'),
    ], required=True, default='other')
    description = fields.Char(required=True)
    quantity = fields.Float(required=True, default=1.0)
    currency_id = fields.Many2one(
        'res.currency', related='booking_id.currency_id', store=True)
    unit_price = fields.Monetary(currency_field='currency_id', required=True)
    subtotal = fields.Monetary(
        currency_field='currency_id', compute='_compute_subtotal', store=True)

    @api.depends('quantity', 'unit_price')
    def _compute_subtotal(self):
        for charge in self:
            charge.subtotal = charge.quantity * charge.unit_price

    @api.constrains('quantity', 'unit_price')
    def _check_amounts(self):
        for charge in self:
            if charge.quantity <= 0:
                raise ValidationError('Quantity must be greater than zero.')
            if charge.unit_price < 0:
                raise ValidationError('Unit price cannot be negative.')

    def _assert_editable(self, bookings, adding=False):
        for booking in bookings:
            if booking.has_live_invoice:
                raise UserError(
                    f"Booking {booking.name} already has an invoice. "
                    f"Cancel the invoice before changing its charges.")
            if adding and booking.state not in ('checked_in', 'checked_out'):
                raise UserError(
                    f"Extra charges can only be added once the guest has "
                    f"checked in (booking {booking.name}).")

    @api.model_create_multi
    def create(self, vals_list):
        booking_ids = {v['booking_id'] for v in vals_list if v.get('booking_id')}
        self._assert_editable(self.env['hotel.booking'].browse(booking_ids), adding=True)
        return super().create(vals_list)

    def write(self, vals):
        self._assert_editable(self.booking_id)
        return super().write(vals)

    def unlink(self):
        self._assert_editable(self.booking_id)
        return super().unlink()
