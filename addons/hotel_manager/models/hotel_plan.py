from odoo import api, fields, models


class HotelPlan(models.Model):
    _name = 'hotel.plan'
    _description = 'Hotel Subscription Plan'
    _order = 'sequence, id'

    _sql_constraints = [
        ('code_unique', 'unique(code)', 'Plan code must be unique.'),
    ]

    name = fields.Char(required=True)
    code = fields.Selection([
        ('free', 'Free Trial'),
        ('starter', 'Starter'),
        ('standard', 'Standard'),
        ('premium', 'Premium'),
    ], required=True)
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)

    # Limits
    max_rooms = fields.Integer(string='Max Rooms', help='0 = Unlimited')
    max_users = fields.Integer(string='Max Users', help='0 = Unlimited')
    has_custom_domain = fields.Boolean(string='Custom Domain')
    has_full_reports = fields.Boolean(string='Full Reports')
    has_priority_support = fields.Boolean(string='Priority Support')
    has_custom_branding = fields.Boolean(string='Custom Branding')

    # Pricing (NGN)
    price_monthly = fields.Float(string='Monthly Price (NGN)')
    price_onetime = fields.Float(string='Setup Fee (NGN)')
    trial_days = fields.Integer(string='Trial Days', default=0)

    description = fields.Text()

    max_rooms_display = fields.Char(string='Max Rooms', compute='_compute_limit_display')
    max_users_display = fields.Char(string='Max Users', compute='_compute_limit_display')

    @api.depends('max_rooms', 'max_users')
    def _compute_limit_display(self):
        for p in self:
            p.max_rooms_display = str(p.max_rooms) if p.max_rooms else 'Unlimited'
            p.max_users_display = str(p.max_users) if p.max_users else 'Unlimited'
