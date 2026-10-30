from odoo import fields, models


class ResCompanySetupFee(models.Model):
    _inherit = 'res.company'

    hotel_charge_setup = fields.Boolean(
        string='Include setup fee in first online payment', default=False,
        help='Off: online payments are the monthly price only. '
             'Turn on for a hotel where the setup fee was agreed to be paid via Paystack.')
