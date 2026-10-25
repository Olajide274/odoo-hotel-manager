from datetime import datetime, time, timedelta

from odoo import api, fields, models

from .license import PACKAGES

PLAN_TO_PACKAGE = {'free': 'trial', 'starter': 'starter',
                   'standard': 'pro', 'premium': 'business'}
SYNC_FIELDS = {'hotel_plan_id', 'hotel_paid_until', 'trial_end_date'}


class ResCompanyLicense(models.Model):
    _inherit = 'res.company'

    hotel_license_package = fields.Char(string='Licence package', compute='_compute_hotel_license')
    hotel_license_status = fields.Char(string='Licence status', compute='_compute_hotel_license')
    hotel_license_expires = fields.Datetime(string='Licence expires', compute='_compute_hotel_license')

    def _compute_hotel_license(self):
        for company in self:
            lic = self.env['hotel.license'].sudo().search(
                [('company_id', '=', company.id)], limit=1)
            company.hotel_license_package = PACKAGES[lic.package]['label'] if lic else ''
            company.hotel_license_status = lic.status if lic else ''
            company.hotel_license_expires = lic.expires_at if lic else False

    def _hotel_sync_license(self):
        License = self.env['hotel.license'].sudo()
        for company in self.sudo():
            plan = company.hotel_plan_id
            package = PLAN_TO_PACKAGE.get(plan.code) if plan else None
            if not package:
                continue
            end = company.trial_end_date if plan.code == 'free' else company.hotel_paid_until
            if end:
                expires = datetime.combine(end, time(23, 59, 59))
            else:
                expires = fields.Datetime.now() + timedelta(days=3650)
            License._set_package(package, expires, company)

    @api.model
    def _hotel_sync_all_licenses(self):
        self.sudo().search([])._hotel_sync_license()

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        companies._hotel_sync_license()
        return companies

    def write(self, vals):
        res = super().write(vals)
        if SYNC_FIELDS & set(vals):
            self._hotel_sync_license()
        return res
