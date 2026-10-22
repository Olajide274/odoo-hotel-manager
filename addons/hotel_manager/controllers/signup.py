import re

from odoo import SUPERUSER_ID, http
from odoo.exceptions import UserError
from odoo.http import request

EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')


def _money(amount):
    return '₦{:,.0f}'.format(amount)


class HotelSignup(http.Controller):

    # ---------- helpers ----------
    def _signup_enabled(self):
        param = request.env['ir.config_parameter'].sudo().get_param('hotel_manager.signup_enabled')
        return param == 'True'

    def _cards(self):
        plans = request.env['hotel.plan'].sudo().search([])
        cards = []
        for p in plans:
            rooms = 'Up to %d rooms' % p.max_rooms if p.max_rooms else 'Unlimited rooms'
            if p.max_users:
                users = '%d user%s' % (p.max_users, '' if p.max_users == 1 else 's')
            else:
                users = 'Unlimited users'
            is_free = p.code == 'free'
            cards.append({
                'code': p.code,
                'name': p.name,
                'description': p.description or '',
                'price': _money(p.price_monthly),
                'period': '' if is_free else '/month',
                'setup': ('%d-day free trial' % (p.trial_days or 7)) if is_free
                         else '+ %s one-time setup' % _money(p.price_onetime),
                'recommended': p.code == 'standard',
                'cta': 'Start free trial' if is_free else 'Choose %s' % p.name,
                'summary': '%s · %s' % (rooms, users),
                'features': [
                    {'text': rooms, 'on': True},
                    {'text': users, 'on': True},
                    {'text': 'Bookings, calendar and billing', 'on': True},
                    {'text': 'Full reports', 'on': p.has_full_reports},
                    {'text': 'Custom domain', 'on': p.has_custom_domain},
                    {'text': 'Custom branding', 'on': p.has_custom_branding},
                    {'text': 'Priority support', 'on': p.has_priority_support},
                ],
            })
        return cards

    def _signup_ctx(self, values=None, selected=None, error=None):
        cards = self._cards()
        codes = [c['code'] for c in cards]
        if selected not in codes:
            selected = 'standard' if 'standard' in codes else (codes[0] if codes else '')
        return {
            'cards': cards,
            'selected': selected,
            'values': values or {},
            'error': error,
            'enabled': self._signup_enabled(),
        }

    def _validate(self, v, password):
        labels = (('hotel_name', 'Hotel name'), ('phone', 'Phone number'),
                  ('contact_name', 'Your name'), ('email', 'Email'))
        for key, label in labels:
            if not v[key]:
                raise UserError('%s is required.' % label)
        if not EMAIL_RE.match(v['email']):
            raise UserError('Please enter a valid email address.')
        if len(password) < 8:
            raise UserError('Your password must be at least 8 characters.')
        env = request.env(user=SUPERUSER_ID)
        if env['res.users'].with_context(active_test=False).search_count([('login', '=', v['email'])]):
            raise UserError('An account with this email already exists. Please log in instead.')
        if not env['hotel.plan'].search_count([('code', '=', v['plan_code'])]):
            raise UserError('Please choose a plan.')

    def _create_account(self, v, password):
        # Superuser env so the public user is NOT linked to the new company
        env = request.env(user=SUPERUSER_ID)
        Plan = env['hotel.plan']
        free = Plan.search([('code', '=', 'free')], limit=1)
        requested = Plan.search([('code', '=', v['plan_code'])], limit=1)
        company_vals = {
            'name': v['hotel_name'],
            'phone': v['phone'],
            'email': v['email'],
            'hotel_plan_id': free.id,
            'hotel_requested_plan_id': requested.id,
        }
        ngn = env.ref('base.NGN', raise_if_not_found=False)
        if ngn:
            company_vals['currency_id'] = ngn.id
        company = env['res.company'].create(company_vals)

        manager = env.ref('hotel_manager.group_hotel_manager')
        internal = env.ref('base.group_user')
        env['res.users'].with_context(no_reset_password=True).create({
            'name': v['contact_name'],
            'login': v['email'],
            'email': v['email'],
            'password': password,
            'company_id': company.id,
            'company_ids': [(6, 0, [company.id])],
            'groups_id': [(6, 0, [internal.id, manager.id])],
        })
        return company

    # ---------- routes ----------
    @http.route('/hotel/pricing', type='http', auth='public', website=True, sitemap=True)
    def pricing(self, **kw):
        return request.render('hotel_manager.pricing_page', {'cards': self._cards()})

    @http.route('/hotel/signup', type='http', auth='public', website=True)
    def signup(self, plan=None, **kw):
        return request.render('hotel_manager.signup_page', self._signup_ctx(selected=plan))

    @http.route('/hotel/signup/submit', type='http', auth='public', website=True,
                methods=['POST'], csrf=True)
    def signup_submit(self, **post):
        if post.get('website_url'):  # honeypot field, humans leave it empty
            return request.redirect('/hotel/pricing')
        keys = ('hotel_name', 'phone', 'contact_name', 'email', 'plan_code')
        values = {k: (post.get(k) or '').strip()[:200] for k in keys}
        values['email'] = values['email'].lower()
        password = post.get('password') or ''

        if not self._signup_enabled():
            return request.render('hotel_manager.signup_page', self._signup_ctx(values, values['plan_code']))
        try:
            self._validate(values, password)
            self._create_account(values, password)
        except UserError as e:
            return request.render('hotel_manager.signup_page',
                                  self._signup_ctx(values, values['plan_code'], str(e)))

        request.env.cr.commit()
        try:
            request.session.authenticate(
                request.db, {'type': 'password', 'login': values['email'], 'password': password})
        except Exception:
            return request.redirect('/web/login')
        return request.redirect('/odoo')
