from odoo import api, fields, models
from odoo.exceptions import ValidationError


class HotelRoom(models.Model):
    _name = 'hotel.room'
    _description = 'Hotel Room'
    _order = 'name'

    name = fields.Char('Room Number', required=True)
    room_type_id = fields.Many2one('hotel.room.type', required=True, ondelete='restrict')
    company_id = fields.Many2one(
        'res.company', required=True, default=lambda self: self.env.company)
    currency_id = fields.Many2one(
        'res.currency',
        required=True,
        default=lambda self: self.env.ref('base.NGN', raise_if_not_found=False) or self.env.company.currency_id,
    )
    price_per_night = fields.Monetary(
        currency_field='currency_id',
        compute='_compute_price_per_night', store=True, readonly=False)
    status = fields.Selection([
        ('available', 'Available'),
        ('occupied', 'Occupied'),
        ('cleaning', 'Cleaning'),
        ('maintenance', 'Maintenance'),
    ], default='available', required=True)
    active = fields.Boolean(default=True)

    _sql_constraints = [
        ('name_company_uniq', 'unique(name, company_id)',
         'A room with this number already exists.'),
    ]

    @api.depends('room_type_id.price_per_night')
    def _compute_price_per_night(self):
        for room in self:
            room.price_per_night = room.room_type_id.price_per_night

    @api.constrains('price_per_night')
    def _check_price(self):
        for room in self:
            if room.price_per_night < 0:
                raise ValidationError('The price per night cannot be negative.')

    @api.constrains('company_id', 'active')
    def _check_plan_room_limit(self):
        for company in self.mapped('company_id'):
            plan = company.sudo().hotel_plan_id
            if not plan or not plan.max_rooms:
                continue  # no plan or unlimited
            count = self.sudo().search_count([('company_id', '=', company.id)])
            if count > plan.max_rooms:
                raise ValidationError(
                    f"Your {plan.name} plan allows {plan.max_rooms} rooms. "
                    "Upgrade your plan to add more.")
