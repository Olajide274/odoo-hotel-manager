from datetime import timedelta

from odoo import api, fields, models


class ResCompany(models.Model):
    _inherit = 'res.company'

    hotel_plan_id = fields.Many2one('hotel.plan', string='Subscription Plan')
    hotel_plan_code = fields.Selection(related='hotel_plan_id.code', store=True)
    trial_end_date = fields.Date(string='Trial End Date')
    is_trial_active = fields.Boolean(string='Trial Active', compute='_compute_is_trial_active')

    def _compute_is_trial_active(self):
        today = fields.Date.context_today(self)
        for company in self:
            company.is_trial_active = bool(
                company.hotel_plan_code == 'free' and
                company.trial_end_date and
                company.trial_end_date >= today
            )

    def _hotel_trial_expired(self):
        """True if the company is on the free plan and its trial has ended."""
        self.ensure_one()
        today = fields.Date.context_today(self)
        return bool(
            self.hotel_plan_id.code == 'free'
            and self.trial_end_date
            and self.trial_end_date < today
        )

    def _set_trial_dates(self):
        today = fields.Date.context_today(self)
        for company in self:
            plan = company.hotel_plan_id
            if plan.code == 'free' and not company.trial_end_date:
                company.trial_end_date = today + timedelta(days=plan.trial_days or 7)

    @api.model_create_multi
    def create(self, vals_list):
        companies = super().create(vals_list)
        companies._set_trial_dates()
        return companies

    def write(self, vals):
        res = super().write(vals)
        if 'hotel_plan_id' in vals:
            self._set_trial_dates()
        return res
