from odoo import fields, models


class HotelRoomType(models.Model):
    _inherit = 'hotel.room.type'

    company_id = fields.Many2one(
        'res.company', string='Hotel', required=True, index=True,
        default=lambda self: self.env.company)
