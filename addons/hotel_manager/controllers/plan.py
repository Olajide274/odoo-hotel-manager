from odoo import fields, http
from odoo.http import request


class HotelPlanPage(http.Controller):

    def _info(self):
        company = request.env.user.company_id.sudo()
        plan = company.hotel_plan_id
        if not plan:
            return None
        today = fields.Date.context_today(company)
        state = company.hotel_subscription_state
        end = company.trial_end_date
        days = max((end - today).days, 0) if end else 0
        if state == 'expired':
            label, css = 'Trial ended', 'danger'
        elif state == 'trial':
            label = 'Free trial · %d day%s left' % (days, '' if days == 1 else 's')
            css = 'warning' if days <= 3 else 'info'
        else:
            label, css = '%s plan' % plan.name, 'success'
        total = plan.trial_days or 7
        return {
            'plan': plan, 'state': state, 'label': label, 'css': css,
            'days': days, 'end': end,
            'end_iso': ('%sT23:59:59' % end) if end else '',
            'pct': min(100, int(days * 100 / total)),
            'paid': getattr(company, 'hotel_paid_until', False),
            'features': [
                ('Full reports', plan.has_full_reports),
                ('Custom domain', plan.has_custom_domain),
                ('Custom branding', plan.has_custom_branding),
                ('Priority support', plan.has_priority_support),
            ],
        }

    @http.route('/hotel/plan/status', type='json', auth='user')
    def status(self):
        info = self._info()
        if not info:
            return {}
        return {'label': info['label'], 'css': info['css'], 'url': '/hotel/my-plan'}

    @http.route('/hotel/my-plan', type='http', auth='user', website=True)
    def page(self, **kw):
        company = request.env.user.company_id.sudo()
        info = self._info()
        limits = {}
        if info:
            rooms = request.env['hotel.room'].sudo().search_count([('company_id', '=', company.id)])
            users = request.env['res.users'].sudo().search_count(
                [('company_ids', 'in', company.id), ('share', '=', False)])
            p = info['plan']
            limits = {'rooms': '%d of %s' % (rooms, p.max_rooms or 'unlimited'),
                      'users': '%d of %s' % (users, p.max_users or 'unlimited')}
        return request.render('hotel_manager.my_plan_page',
                              {'company': company, 'info': info, 'limits': limits})
