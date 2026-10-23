import socket
from urllib.parse import quote

from odoo import SUPERUSER_ID, http
from odoo.exceptions import UserError
from odoo.http import request

from .signup import HotelSignup

DISPOSABLE = {
    'mailinator.com', 'guerrillamail.com', '10minutemail.com', 'tempmail.com',
    'temp-mail.org', 'yopmail.com', 'trashmail.com', 'sharklasers.com',
    'getnada.com', 'dispostable.com', 'maildrop.cc', 'throwawaymail.com',
    'fakeinbox.com',
}
COMMON = {
    'password', 'password1', 'password123', '12345678', '123456789', 'qwerty123',
    'qwertyuiop', 'iloveyou', 'admin123', 'welcome1', 'letmein123', 'abc12345',
    '11111111',
}
PROBLEMS = {
    'wait': 'Please wait a minute before asking for another email.',
    'limit': 'Too many emails requested today. Please try again tomorrow.',
    'failed': 'We could not send the email just now. Please try again shortly.',
}


def check_password(password, email=''):
    if len(password) < 8:
        raise UserError('Your password must be at least 8 characters.')
    low = password.lower()
    if low in COMMON or password.isdigit():
        raise UserError('That password is too easy to guess. Please choose another.')
    if email and (low == email.lower() or low == email.split('@')[0].lower()):
        raise UserError('Your password cannot be the same as your email.')


def check_disposable(email):
    domain = email.rsplit('@', 1)[-1].lower()
    if domain in DISPOSABLE:
        raise UserError('Please use a permanent email address, not a disposable one.')


def _domain_has_mail(domain):
    """True if the domain can receive mail. Fails open on timeouts."""
    try:
        import dns.resolver as r
    except ImportError:
        r = None
    if r is None:
        try:
            socket.getaddrinfo(domain, None)
            return True
        except socket.gaierror:
            return False
        except Exception:
            return True
    try:
        r.resolve(domain, 'MX', lifetime=5)
        return True
    except r.NoAnswer:
        try:
            r.resolve(domain, 'A', lifetime=5)
            return True
        except (r.NXDOMAIN, r.NoAnswer):
            return False
        except Exception:
            return True
    except r.NXDOMAIN:
        return False
    except Exception:
        return True


def check_email_domain(email):
    check_disposable(email)
    domain = email.rsplit('@', 1)[-1].lower()
    if not _domain_has_mail(domain):
        raise UserError('We could not find a mail server for "%s". Please check the spelling.' % domain)


class HotelSignupVerified(HotelSignup):

    # ---------- helpers ----------
    def _base_url(self):
        param = request.env['ir.config_parameter'].sudo().get_param('hotel_manager.public_url')
        return (param or request.httprequest.host_url).rstrip('/')

    def _msg(self, title, text, link_url=None, link_label=None, show_resend=False, email=''):
        return request.render('hotel_manager.verify_message_page', {
            'title': title, 'text': text,
            'link_url': link_url, 'link_label': link_label,
            'show_resend': show_resend,
            'resend_url': '/hotel/verify/resend?email=%s' % quote(email or ''),
        })

    def _create_account(self, v, password):
        company = super()._create_account(v, password)
        env = request.env(user=SUPERUSER_ID)
        user = env['res.users'].with_context(active_test=False).search(
            [('login', '=', v['email'])], limit=1)
        user.write({'active': False})
        return company

    # ---------- signup ----------
    @http.route('/hotel/signup/submit', type='http', auth='public', website=True,
                methods=['POST'], csrf=True)
    def signup_submit(self, **post):
        if not request.env.user._is_public():
            return request.redirect('/odoo')
        if post.get('website_url'):
            return request.redirect('/hotel/pricing')
        keys = ('hotel_name', 'phone', 'contact_name', 'email', 'plan_code')
        values = {k: (post.get(k) or '').strip()[:200] for k in keys}
        values['email'] = values['email'].lower()
        password = post.get('password') or ''

        def again(error=None):
            return request.render('hotel_manager.signup_page',
                                  self._signup_ctx(values, values['plan_code'], error))

        if not self._signup_enabled():
            return again()

        Users = request.env['res.users'].sudo().with_context(active_test=False)
        Token = request.env['hotel.signup.token'].sudo()
        try:
            if password != (post.get('password_confirm') or ''):
                raise UserError('The two passwords do not match.')
            if not values['email'] or '@' not in values['email']:
                raise UserError('Please enter a valid email address.')
            check_password(password, values['email'])
            existing = Users.search([('login', '=', values['email'])], limit=1)
            if existing and not existing.active and Token.search_count([('user_id', '=', existing.id)]):
                return request.redirect('/hotel/verify/resend?email=%s' % quote(values['email']))
            check_email_domain(values['email'])
            self._validate(values, password)
            self._create_account(values, password)
        except UserError as e:
            return again(str(e))

        user = Users.search([('login', '=', values['email'])], limit=1)
        problem = Token.send_verification(user, self._base_url())
        if problem:
            return self._msg(
                'Account created, email not sent', PROBLEMS[problem],
                show_resend=True, email=values['email'])
        return self._msg(
            'Check your email',
            'We sent a confirmation link to %s. It expires in 24 hours.' % values['email'],
            show_resend=True, email=values['email'])

    # ---------- verification ----------
    @http.route('/hotel/verify/<string:token>', type='http', auth='public', website=True)
    def verify_page(self, token, **kw):
        if request.env['hotel.signup.token'].sudo().lookup(token):
            return request.render('hotel_manager.verify_confirm_page', {'token': token})
        return self._msg('This link has expired',
                         'The link is invalid, already used or older than 24 hours.',
                         show_resend=True)

    @http.route('/hotel/verify/<string:token>/confirm', type='http', auth='public',
                website=True, methods=['POST'], csrf=True)
    def verify_confirm(self, token, **kw):
        user = request.env['hotel.signup.token'].sudo().consume(token)
        if not user:
            return self._msg('This link has expired',
                             'The link is invalid, already used or older than 24 hours.',
                             show_resend=True)
        return self._msg('Email confirmed',
                         'Your free trial has started. Log in to set up your hotel.',
                         link_url='/web/login?login=%s' % quote(user.login),
                         link_label='Log in')

    @http.route('/hotel/verify/resend', type='http', auth='public', website=True)
    def resend_page(self, email='', **kw):
        return request.render('hotel_manager.verify_resend_page', {'email': email, 'done': False})

    @http.route('/hotel/verify/resend/submit', type='http', auth='public', website=True,
                methods=['POST'], csrf=True)
    def resend_submit(self, email='', **kw):
        email = (email or '').strip().lower()[:200]
        user = request.env['res.users'].sudo().with_context(active_test=False).search(
            [('login', '=', email)], limit=1)
        Token = request.env['hotel.signup.token'].sudo()
        if user and not user.active and Token.search_count([('user_id', '=', user.id)]):
            Token.send_verification(user, self._base_url())
        return request.render('hotel_manager.verify_resend_page', {'email': email, 'done': True})
