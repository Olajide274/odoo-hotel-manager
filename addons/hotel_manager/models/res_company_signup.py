from odoo import fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    hotel_requested_plan_id = fields.Many2one(
        'hotel.plan', string='Requested Plan',
        help='Plan chosen at signup, to be activated after payment.')
