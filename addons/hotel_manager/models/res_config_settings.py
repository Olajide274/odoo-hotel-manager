from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    paystack_secret_key = fields.Char(
        string='Paystack Secret Key',
        config_parameter='hotel_manager.paystack_secret_key')
    paystack_public_key = fields.Char(
        string='Paystack Public Key',
        config_parameter='hotel_manager.paystack_public_key')
