from odoo import api, fields, models
import re
import unicodedata


def slugify(text):
    text = unicodedata.normalize('NFKD', text or '').encode('ascii', 'ignore').decode()
    return re.sub(r'[^a-z0-9]+', '-', text.lower()).strip('-')



class ResCompanyBookingSlug(models.Model):
    _inherit = 'res.company'

    hotel_booking_slug = fields.Char(string='Booking link name', copy=False, index=True)

    _sql_constraints = [
        ('hotel_booking_slug_uniq', 'unique(hotel_booking_slug)', 'This booking link name is taken.'),
    ]

    def _hotel_make_slug(self):
        for company in self.sudo():
            if company.hotel_booking_slug:
                continue
            base = slugify(company.name) or 'hotel'
            slug, n = base, 1
            while self.sudo().search_count([('hotel_booking_slug', '=', slug)]):
                n += 1
                slug = '%s-%d' % (base, n)
            company.hotel_booking_slug = slug

    @api.model
    def _hotel_backfill_slugs(self):
        self.sudo().search([])._hotel_make_slug()

    def _hotel_public_rooms(self):
        self.ensure_one()
        return self.env['hotel.room'].sudo().search([
            ('company_id', '=', self.id), ('status', '=', 'available'), ('active', '=', True)])

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        companies._hotel_make_slug()
        return companies
