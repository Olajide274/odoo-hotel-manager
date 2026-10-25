from odoo import api, fields, models


def _company_of(env, vals):
    cid = vals.get('company_id')
    return env['res.company'].sudo().browse(cid) if cid else env.company


class HotelBookingLicense(models.Model):
    _inherit = 'hotel.booking'

    has_billing = fields.Boolean(compute='_compute_license_flags')
    license_notice = fields.Char(compute='_compute_license_flags')

    def _compute_license_flags(self):
        License = self.env['hotel.license']
        for booking in self:
            booking.has_billing = License.has_feature('billing', booking.company_id)
            booking.license_notice = License.notice(booking.company_id)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            self.env['hotel.license'].assert_active(_company_of(self.env, vals))
        return super().create(vals_list)

    def write(self, vals):
        for booking in self:
            self.env['hotel.license'].assert_active(booking.company_id)
        return super().write(vals)

    def unlink(self):
        for booking in self:
            self.env['hotel.license'].assert_active(booking.company_id)
        return super().unlink()

    def action_create_invoice(self):
        for booking in self:
            self.env['hotel.license'].require('billing', booking.company_id)
        return super().action_create_invoice()


class HotelBookingChargeLicense(models.Model):
    _inherit = 'hotel.booking.charge'

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            booking = self.env['hotel.booking'].sudo().browse(vals.get('booking_id'))
            self.env['hotel.license'].require(
                'billing', booking.company_id if booking.exists() else self.env.company)
        return super().create(vals_list)


class HotelRoomLicense(models.Model):
    _inherit = 'hotel.room'

    @api.model_create_multi
    def create(self, vals_list):
        counts = {}
        for vals in vals_list:
            company = _company_of(self.env, vals)
            counts[company.id] = counts.get(company.id, 0) + 1
        for cid, n in counts.items():
            self.env['hotel.license'].check_room_limit(
                n, self.env['res.company'].sudo().browse(cid))
        return super().create(vals_list)
