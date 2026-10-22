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

    hotel_subscription_state = fields.Selection(
        [('trial', 'Trial'), ('expired', 'Trial expired'), ('active', 'Active')],
        compute='_compute_hotel_subscription_state')

    @api.depends('hotel_plan_id', 'hotel_plan_id.code', 'trial_end_date')
    def _compute_hotel_subscription_state(self):
        for company in self:
            if not company.hotel_plan_id:
                company.hotel_subscription_state = 'active'
            elif company._hotel_trial_expired():
                company.hotel_subscription_state = 'expired'
            elif company.hotel_plan_id.code == 'free':
                company.hotel_subscription_state = 'trial'
            else:
                company.hotel_subscription_state = 'active'

    def hotel_subscription_notification(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        state = self.hotel_subscription_state
        if state == 'expired':
            title, kind = 'Free trial ended', 'danger'
            msg = 'Your free trial ended on %s. New bookings are blocked until you upgrade. %%s' % self.trial_end_date
        elif state == 'trial':
            left = (self.trial_end_date - today).days if self.trial_end_date else 0
            title, kind = 'Free trial', ('warning' if left <= 3 else 'info')
            msg = 'Your free trial has %d day(s) left (ends %s). %%s' % (left, self.trial_end_date)
        else:
            title, kind = 'Subscription', 'success'
            msg = 'Your %s plan is active. %%s' % (self.hotel_plan_id.name or 'current')
        return {
            'type': 'ir.actions.client', 'tag': 'display_notification',
            'params': {'title': title, 'message': msg, 'type': kind, 'sticky': True,
                       'links': [{'label': 'View plans', 'url': '/hotel/pricing'}]},
        }

    @api.model
    def _cron_hotel_trial_reminders(self):
        import logging
        from odoo.tools import html_escape
        _logger = logging.getLogger(__name__)
        today = fields.Date.context_today(self)
        base = self.env['ir.config_parameter'].sudo().get_param('web.base.url', '')
        for days in (3, 1, 0, -1):
            target = today + timedelta(days=days)
            for company in self.sudo().search([('hotel_plan_code', '=', 'free'),
                                               ('trial_end_date', '=', target)]):
                if not company.email:
                    continue
                if days > 0:
                    subject = 'Your free trial ends in %d day(s)' % days
                elif days == 0:
                    subject = 'Your free trial ends today'
                else:
                    subject = 'Your free trial has ended'
                body = ('<p>Hello,</p><p>%s for <b>%s</b> (trial end date: %s).</p>'
                        '<p><a href="%s/hotel/pricing">Choose a plan</a> to keep creating bookings.</p>'
                        % (subject, html_escape(company.name), company.trial_end_date, base))
                try:
                    with self.env.cr.savepoint():
                        self.env['mail.mail'].sudo().create({
                            'subject': subject, 'body_html': body,
                            'email_to': company.email, 'auto_delete': True})
                except Exception:
                    _logger.exception('Trial reminder failed for %s', company.name)
