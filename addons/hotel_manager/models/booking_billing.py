from odoo import api, fields, models
from odoo.exceptions import UserError


class HotelBookingBilling(models.Model):
    _inherit = 'hotel.booking'

    partner_id = fields.Many2one('res.partner', string='Guest Contact', copy=False)
    charge_ids = fields.One2many(
        'hotel.booking.charge', 'booking_id', string='Extra Charges', copy=False)
    charges_total = fields.Monetary(
        currency_field='currency_id', compute='_compute_charges_total', store=True)
    folio_total = fields.Monetary(
        currency_field='currency_id', compute='_compute_folio_total', store=True)
    invoice_id = fields.Many2one(
        'account.move', string='Invoice', readonly=True, copy=False, ondelete='set null')
    has_live_invoice = fields.Boolean(compute='_compute_has_live_invoice')
    payment_state = fields.Selection(
        related='invoice_id.payment_state', string='Payment Status')

    @api.depends('charge_ids.subtotal')
    def _compute_charges_total(self):
        for booking in self:
            booking.charges_total = sum(booking.charge_ids.mapped('subtotal'))

    @api.depends('total_price', 'charges_total')
    def _compute_folio_total(self):
        for booking in self:
            booking.folio_total = booking.total_price + booking.charges_total

    @api.depends('invoice_id.state')
    def _compute_has_live_invoice(self):
        for booking in self:
            booking.has_live_invoice = bool(
                booking.invoice_id and booking.invoice_id.state != 'cancel')

    def _get_invoice_partner(self):
        """Return the guest's contact, reusing one with the same email or phone."""
        self.ensure_one()
        if not self.partner_id:
            Partner = self.env['res.partner']
            partner = Partner
            if self.guest_email:
                partner = Partner.search([('email', '=ilike', self.guest_email)], limit=1)
            if not partner and self.guest_phone:
                partner = Partner.search([('phone', '=', self.guest_phone)], limit=1)
            if not partner:
                partner = Partner.create({
                    'name': self.guest_name,
                    'phone': self.guest_phone or False,
                    'email': self.guest_email or False,
                })
            self.partner_id = partner
        return self.partner_id

    def action_create_invoice(self):
        self.ensure_one()
        if self.has_live_invoice:
            raise UserError(f"Booking {self.name} already has an invoice.")
        if self.state not in ('checked_in', 'checked_out'):
            raise UserError('Invoices can only be created for checked-in or checked-out bookings.')
        journal = self.env['account.journal'].search([
            ('type', '=', 'sale'), ('company_id', '=', self.company_id.id),
        ], limit=1)
        if not journal or not journal.default_account_id:
            raise UserError(
                'No sales journal with an income account was found. '
                'Set up the accounting chart in the Invoicing settings first.')
        # tax_ids is forced empty so the invoice total equals the folio total.
        lines = [(0, 0, {
            'name': (f"Room {self.room_id.name} ({self.room_type_id.name}): "
                     f"{self.check_in} to {self.check_out}"),
            'quantity': self.nights,
            'price_unit': self.price_per_night,
            'tax_ids': [(6, 0, [])],
        })]
        for charge in self.charge_ids:
            category = dict(charge._fields['category'].selection)[charge.category]
            lines.append((0, 0, {
                'name': f"{category}: {charge.description}",
                'quantity': charge.quantity,
                'price_unit': charge.unit_price,
                'tax_ids': [(6, 0, [])],
            }))
        invoice = self.env['account.move'].create({
            'move_type': 'out_invoice',
            'partner_id': self._get_invoice_partner().id,
            'journal_id': journal.id,
            'invoice_date': fields.Date.context_today(self),
            'invoice_origin': self.name,
            'invoice_line_ids': lines,
        })
        self.invoice_id = invoice
        return self.action_view_invoice()

    def action_view_invoice(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'account.action_move_out_invoice_type')
        action.update({
            'res_id': self.invoice_id.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
        })
        return action
