import logging
import uuid
from urllib.parse import quote

import requests

from odoo import http
from odoo.http import request

_logger = logging.getLogger(__name__)
PAYSTACK = 'https://api.paystack.co'


class HotelSubscribe(http.Controller):

    def _is_manager(self):
        return request.env.user.has_group('hotel_manager.group_hotel_manager')

    def _first_payment(self, company):
        return not request.env['hotel.subscription.payment'].sudo().search_count(
            [('company_id', '=', company.id), ('state', '=', 'paid')])

    @http.route('/hotel/upgrade', type='http', auth='user', website=True)
    def upgrade(self, error=None, **kw):
        if not self._is_manager():
            return request.redirect('/odoo')
        company = request.env.user.company_id.sudo()
        plans = request.env['hotel.plan'].sudo().search([('code', '!=', 'free')])
        return request.render('hotel_manager.upgrade_page', {
            'company': company, 'plans': plans, 'first': self._first_payment(company),
            'error': 'Payment is unavailable right now. Please try again shortly.' if error else None})

    @http.route('/hotel/subscribe/<string:plan_code>', type='http', auth='user', website=True)
    def subscribe(self, plan_code, **kw):
        if not self._is_manager():
            return request.redirect('/odoo')
        company = request.env.user.company_id.sudo()
        plan = request.env['hotel.plan'].sudo().search(
            [('code', '=', plan_code), ('code', '!=', 'free')], limit=1)
        ICP = request.env['ir.config_parameter'].sudo()
        secret = ICP.get_param('hotel_manager.paystack_secret_key') or ''
        amount = (plan.price_monthly + (plan.price_onetime if self._first_payment(company) else 0.0)) if plan else 0
        if not plan or not secret or amount <= 0:
            return request.redirect('/hotel/upgrade?error=1')
        reference = 'SUB-%d-%s' % (company.id, uuid.uuid4().hex[:10])
        base = (ICP.get_param('web.base.url') or '').rstrip('/')
        payload = {
            'email': request.env.user.email or company.email,
            'amount': round(amount * 100), 'currency': 'NGN', 'reference': reference,
            'callback_url': base + '/hotel/subscribe/callback',
            'metadata': {'company_id': company.id, 'plan': plan.code},
        }
        try:
            resp = requests.post(PAYSTACK + '/transaction/initialize', json=payload,
                                 headers={'Authorization': 'Bearer %s' % secret}, timeout=15).json()
            url = (resp.get('data') or {}).get('authorization_url') if resp.get('status') else None
        except Exception:
            _logger.exception('Paystack initialize failed')
            url = None
        if not url:
            return request.redirect('/hotel/upgrade?error=1')
        request.env['hotel.subscription.payment'].sudo().create({
            'company_id': company.id, 'plan_id': plan.id, 'reference': reference, 'amount': amount})
        return request.redirect(url, local=False)

    @http.route('/hotel/subscribe/callback', type='http', auth='user', website=True)
    def callback(self, **kw):
        ref = kw.get('reference') or kw.get('trxref') or ''
        pay = request.env['hotel.subscription.payment'].sudo().search(
            [('reference', '=', ref), ('company_id', '=', request.env.user.company_id.id)], limit=1)
        if pay and pay.state != 'paid':
            secret = request.env['ir.config_parameter'].sudo().get_param('hotel_manager.paystack_secret_key') or ''
            try:
                r = requests.get('%s/transaction/verify/%s' % (PAYSTACK, quote(ref, safe='')),
                                 headers={'Authorization': 'Bearer %s' % secret}, timeout=15).json()
                if r.get('status'):
                    pay._confirm_paystack(r.get('data') or {})
            except Exception:
                _logger.exception('Paystack verify failed for %s', ref)
        return request.redirect('/odoo')
