from odoo import api, fields, models


class HotelRoomType(models.Model):
    _name = 'hotel.room.type'
    _description = 'Hotel Room Type'
    _order = 'name'

    name = fields.Char(required=True)
    description = fields.Text()
    capacity = fields.Integer(default=2)
    currency_id = fields.Many2one(
        'res.currency', required=True,
        default=lambda self: self.env.company.currency_id)
    price_per_night = fields.Monetary(currency_field='currency_id', required=True)
    room_ids = fields.One2many('hotel.room', 'room_type_id')
    room_count = fields.Integer(compute='_compute_room_count')

    @api.depends('room_ids')
    def _compute_room_count(self):
        for rec in self:
            rec.room_count = len(rec.room_ids)
