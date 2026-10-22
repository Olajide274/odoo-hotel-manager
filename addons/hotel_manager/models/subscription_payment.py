import logging
from datetime import timedelta

from odoo import fields, models

_logger = logging.getLogger(__name__)


class HotelSubscriptionPayment(models.Model):
    _name = 'hotel.subscription.payment'
    _description = 'Hotel subscription payment'
    _order = 'id desc'
    _sql_constraints = [('reference_unique', 'unique(reference)', 'Reference must be unique.')]

    company_id = fields.Many2one('res.company', required=True, index=True, ondelete='cascade')
    plan_id = fields.Many2one('hotel.plan', required=True)
    reference = fields.Char(required=True, index=True, readonly=True)
    amount = fields.Float(string='Amount (NGN)', required=True)
    state = fields.Selection([('pending', 'Pending'), ('paid', 'Paid'), ('failed', 'Failed')],
                             default='pending', required=True)
    paid_date = fields.Datetime()

    def _confirm_paystack(self, data):
        """Idempotent. `data` is Paystack's transaction data (webhook or verify API)."""
        self.ensure_one()
        self.env.cr.execute("SELECT state FROM hotel_subscription_payment WHERE id = %s FOR UPDATE", (self.id,))
        row = self.env.cr.fetchone()
        self.invalidate_recordset(['state'])
        if not row:
            return False
        if row[0] == 'paid':
            return True
        if (data.get('status') != 'success'
                or data.get('currency') != 'NGN'
                or data.get('reference') != self.reference
                or int(data.get('amount') or 0) != round(self.amount * 100)):
            _logger.warning('Paystack: rejected payment %s (mismatch)', self.reference)
            return False
        company = self.company_id.sudo()
        today = fields.Date.context_today(self)
        start = max(today, company.hotel_paid_until or today)
        company.write({'hotel_plan_id': self.plan_id.id, 'hotel_paid_until': start + timedelta(days=30)})
        self.write({'state': 'paid', 'paid_date': fields.Datetime.now()})
        return True


class ResCompanyPaid(models.Model):
    _inherit = 'res.company'

    hotel_paid_until = fields.Date(string='Paid Until', copy=False)

    def _hotel_trial_expired(self):
        self.ensure_one()
        if super()._hotel_trial_expired():
            return True
        today = fields.Date.context_today(self)
        return bool(self.hotel_plan_id and self.hotel_plan_id.code != 'free'
                    and self.hotel_paid_until and self.hotel_paid_until < today)

    def _compute_hotel_subscription_state(self):
        super()._compute_hotel_subscription_state()
        for c in self:
            if c.hotel_plan_id and c.hotel_plan_id.code != 'free' and c._hotel_trial_expired():
                c.hotel_subscription_state = 'expired'
