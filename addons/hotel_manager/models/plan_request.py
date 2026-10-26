from datetime import timedelta

from markupsafe import escape

from odoo import api, fields, models


class HotelPlanRequest(models.Model):
    _name = 'hotel.plan.request'
    _description = 'Request to activate a plan manually'
    _order = 'id desc'

    company_id = fields.Many2one('res.company', required=True, ondelete='cascade')
    plan_id = fields.Many2one('hotel.plan', required=True)
    contact_name = fields.Char()
    phone = fields.Char()
    note = fields.Text()
    state = fields.Selection([('new', 'New'), ('done', 'Activated')], default='new', required=True)

    @api.model
    def submit(self, company, plan, user, phone, note):
        """Returns (record, created). One open request per hotel per hour."""
        recent = self.sudo().search([
            ('company_id', '=', company.id), ('state', '=', 'new'),
            ('create_date', '>', fields.Datetime.now() - timedelta(hours=1))], limit=1)
        if recent:
            return recent, False
        rec = self.sudo().create({
            'company_id': company.id, 'plan_id': plan.id, 'contact_name': user.name,
            'phone': (phone or '')[:40], 'note': (note or '')[:1000]})
        rec._notify_admin()
        return rec, True

    def _notify_admin(self):
        ICP = self.env['ir.config_parameter'].sudo()
        to = ICP.get_param('hotel_manager.notify_email') or 'swiftdigitalservices00@gmail.com'
        sender = ICP.get_param('mail.default.from') or to
        for rec in self:
            body = ('<p>%s asked to activate the <b>%s</b> plan.</p>'
                    '<p>Hotel: %s<br/>Contact: %s, %s</p><p>Note: %s</p>'
                    '<p>Activate it under Settings, Companies, Licence tab.</p>') % (
                escape(rec.company_id.name), escape(rec.plan_id.name),
                escape(rec.company_id.name), escape(rec.contact_name or ''),
                escape(rec.phone or ''), escape(rec.note or ''))
            try:
                with self.env.cr.savepoint():
                    self.env['mail.mail'].sudo().create({
                        'subject': 'Plan activation request: %s' % rec.company_id.name,
                        'body_html': body, 'email_to': to, 'email_from': sender,
                        'auto_delete': True})
            except Exception:
                pass


class HotelPlanActivateRequests(models.TransientModel):
    _inherit = 'hotel.plan.activate'

    def action_activate(self):
        res = super().action_activate()
        self.env['hotel.plan.request'].sudo().search([
            ('company_id', '=', self.company_id.id), ('state', '=', 'new')]).write({'state': 'done'})
        return res
