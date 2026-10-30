from datetime import timedelta

from odoo import fields, models
from odoo.exceptions import AccessError, UserError


class HotelPlanActivation(models.Model):
    _name = 'hotel.plan.activation'
    _description = 'Manual plan activation log'
    _order = 'id desc'

    company_id = fields.Many2one('res.company', required=True, ondelete='cascade')
    plan_id = fields.Many2one('hotel.plan', required=True)
    days = fields.Integer()
    paid_until = fields.Date()
    note = fields.Char()
    activated_by = fields.Many2one('res.users', default=lambda self: self.env.user)
    activated_on = fields.Datetime(default=fields.Datetime.now)


class HotelPlanActivate(models.TransientModel):
    _name = 'hotel.plan.activate'
    _description = 'Activate a hotel plan manually'

    company_id = fields.Many2one('res.company', required=True)
    plan_id = fields.Many2one('hotel.plan', required=True)
    days = fields.Integer(default=30, required=True)
    note = fields.Char()

    def action_activate(self):
        self.ensure_one()
        if not (self.env.su or self.env.user.has_group('base.group_system')):
            raise AccessError('Only an administrator can activate a plan manually.')
        if self.days <= 0:
            raise UserError('Days must be more than zero.')
        company = self.company_id.sudo()
        plan = self.plan_id
        today = fields.Date.context_today(self)
        if plan.code == 'free':
            vals = {'hotel_plan_id': plan.id, 'trial_end_date': today + timedelta(days=self.days)}
            until = vals['trial_end_date']
        else:
            start = max(today, company.hotel_paid_until or today)
            until = start + timedelta(days=self.days)
            vals = {'hotel_plan_id': plan.id, 'hotel_paid_until': until}
        company.write(vals)
        self.env['hotel.plan.activation'].sudo().create({
            'company_id': company.id, 'plan_id': plan.id, 'days': self.days,
            'paid_until': until, 'note': self.note})
        return {'type': 'ir.actions.client', 'tag': 'reload'}
