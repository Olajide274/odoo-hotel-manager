from odoo import _, api, models
from odoo.exceptions import UserError


class HotelBookingExpiry(models.Model):
    _inherit = 'hotel.booking'

    @api.model_create_multi
    def create(self, vals_list):
        Company = self.env['res.company'].sudo()
        for vals in vals_list:
            company = Company.browse(vals['company_id']) if vals.get('company_id') else self.env.company.sudo()
            if company._hotel_trial_expired():
                raise UserError(_(
                    'Your free trial ended on %s. Please upgrade your plan (/hotel/pricing) to create new bookings.'
                ) % company.trial_end_date)
        return super().create(vals_list)
