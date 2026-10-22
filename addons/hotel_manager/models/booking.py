from datetime import timedelta

from odoo import api, fields, models
from odoo.exceptions import UserError, ValidationError

# Bookings in these states hold the room. Cancelled and checked-out ones do not.
ACTIVE_STATES = ('draft', 'confirmed', 'checked_in')


class HotelBooking(models.Model):
    _name = 'hotel.booking'
    _description = 'Hotel Booking'
    _order = 'check_in desc, id desc'

    name = fields.Char('Reference', default='New', readonly=True, copy=False)
    guest_name = fields.Char(required=True)
    guest_phone = fields.Char()
    guest_email = fields.Char()
    room_id = fields.Many2one('hotel.room', required=True, ondelete='restrict')
    room_type_id = fields.Many2one(related='room_id.room_type_id', string='Room Type')
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency',
        required=True,
        default=lambda self: self.env.ref('base.NGN', raise_if_not_found=False) or self.env.company.currency_id,
    )
    check_in = fields.Date(required=True, default=fields.Date.context_today)
    check_out = fields.Date(
        required=True,
        default=lambda self: fields.Date.context_today(self) + timedelta(days=1))
    nights = fields.Integer(compute='_compute_nights', store=True)
    price_per_night = fields.Monetary(
        currency_field='currency_id',
        compute='_compute_price_per_night', store=True, readonly=False)
    total_price = fields.Monetary(
        currency_field='currency_id', compute='_compute_total_price', store=True)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('confirmed', 'Confirmed'),
        ('checked_in', 'Checked In'),
        ('checked_out', 'Checked Out'),
        ('cancelled', 'Cancelled'),
    ], default='draft', required=True, copy=False)

    # ---------- computes ----------
    @api.depends('check_in', 'check_out')
    def _compute_nights(self):
        for booking in self:
            if booking.check_in and booking.check_out:
                booking.nights = max((booking.check_out - booking.check_in).days, 0)
            else:
                booking.nights = 0

    # Depends only on the room, so the price is a snapshot taken at booking time.
    @api.depends('room_id')
    def _compute_price_per_night(self):
        for booking in self:
            booking.price_per_night = booking.room_id.price_per_night

    @api.depends('nights', 'price_per_night')
    def _compute_total_price(self):
        for booking in self:
            booking.total_price = booking.nights * booking.price_per_night

    # ---------- constraints ----------
    @api.constrains('check_in', 'check_out')
    def _check_dates(self):
        for booking in self:
            if booking.check_in and booking.check_out and booking.check_out <= booking.check_in:
                raise ValidationError('Check-out must be after check-in.')

    @api.constrains('room_id', 'check_in', 'check_out', 'state')
    def _check_overlap(self):
        for booking in self:
            if booking.state not in ACTIVE_STATES:
                continue
            if not (booking.room_id and booking.check_in and booking.check_out):
                continue
            # Same-day turnover is allowed: the other stay must start before our
            # check-out AND end after our check-in to count as an overlap.
            clash = self.search([
                ('id', '!=', booking.id),
                ('room_id', '=', booking.room_id.id),
                ('state', 'in', ACTIVE_STATES),
                ('check_in', '<', booking.check_out),
                ('check_out', '>', booking.check_in),
            ], limit=1)
            if clash:
                raise ValidationError(
                    f"Room {booking.room_id.name} is already booked from "
                    f"{clash.check_in} to {clash.check_out} ({clash.name}).")

    # ---------- create / delete ----------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', 'New') == 'New':
                vals['name'] = self.env['ir.sequence'].next_by_code('hotel.booking') or 'New'
        return super().create(vals_list)

    @api.ondelete(at_uninstall=False)
    def _unlink_except_active(self):
        for booking in self:
            if booking.state not in ('draft', 'cancelled'):
                raise UserError('Only draft or cancelled bookings can be deleted.')

    # ---------- state changes ----------
    def _require_state(self, allowed, verb):
        for booking in self:
            if booking.state not in allowed:
                raise UserError(
                    f"Booking {booking.name} is {booking.state.replace('_', ' ')} "
                    f"and cannot be {verb}.")

    def action_confirm(self):
        self._require_state(('draft',), 'confirmed')
        self.write({'state': 'confirmed'})
        return True

    def action_check_in(self):
        self._require_state(('confirmed',), 'checked in')
        for booking in self:
            if booking.room_id.status in ('occupied', 'maintenance'):
                raise UserError(
                    f"Room {booking.room_id.name} is {booking.room_id.status} "
                    f"and cannot be checked into.")
        for booking in self:
            booking.room_id.status = 'occupied'
        self.write({'state': 'checked_in'})
        return True

    def action_check_out(self):
        self._require_state(('checked_in',), 'checked out')
        for booking in self:
            booking.room_id.status = 'cleaning'
        self.write({'state': 'checked_out'})
        return True

    def action_cancel(self):
        self._require_state(('draft', 'confirmed'), 'cancelled')
        self.write({'state': 'cancelled'})
        return True

    def action_reset_draft(self):
        self._require_state(('cancelled',), 'reset to draft')
        self.write({'state': 'draft'})
        return True
