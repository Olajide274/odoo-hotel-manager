from urllib.parse import quote

from odoo import http
from odoo.http import request

WA_NUMBER = '2348165212254'


class HotelActivationRequest(http.Controller):

    def _guard(self):
        user = request.env.user
        if user._is_public() or not user.has_group('hotel_manager.group_hotel_manager'):
            return None
        return user

    def _plan(self, code):
        return request.env['hotel.plan'].sudo().search(
            [('code', '=', code), ('code', '!=', 'free')], limit=1)

    @http.route('/hotel/activate-request/<string:plan_code>', type='http', auth='user', website=True)
    def page(self, plan_code, **kw):
        user = self._guard()
        plan = self._plan(plan_code)
        if not user or not plan:
            return request.redirect('/hotel/upgrade')
        company = user.company_id.sudo()
        wa = 'https://wa.me/%s?text=%s' % (WA_NUMBER, quote(
            'Hi, I am %s from %s. I would like to activate the %s plan.' % (
                user.name, company.name, plan.name)))
        return request.render('hotel_manager.activation_request_page', {
            'plan': plan, 'company': company, 'wa_url': wa, 'done': False, 'again': False,
            'phone': company.phone or ''})

    @http.route('/hotel/activate-request/<string:plan_code>/submit', type='http', auth='user',
                website=True, methods=['POST'], csrf=True)
    def submit(self, plan_code, phone='', note='', **kw):
        user = self._guard()
        plan = self._plan(plan_code)
        if not user or not plan:
            return request.redirect('/hotel/upgrade')
        company = user.company_id.sudo()
        _rec, created = request.env['hotel.plan.request'].submit(company, plan, user, phone, note)
        return request.render('hotel_manager.activation_request_page', {
            'plan': plan, 'company': company, 'wa_url': '', 'done': True,
            'again': not created, 'phone': phone})
