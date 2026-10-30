import hashlib
import secrets
from datetime import timedelta

from markupsafe import escape

from odoo import api, fields, models

TOKEN_HOURS = 24
RESEND_SECONDS = 60
MAX_PER_DAY = 5


def _hash(raw):
    return hashlib.sha256((raw or '').encode()).hexdigest()


class HotelSignupToken(models.Model):
    _name = 'hotel.signup.token'
    _description = 'Hotel signup email verification token'

    user_id = fields.Many2one('res.users', required=True, ondelete='cascade', index=True)
    token_hash = fields.Char(required=True, index=True)
    expires_at = fields.Datetime(required=True)
    revoked = fields.Boolean(default=False)

    @api.model
    def issue(self, user):
        """Return (raw_token, None) or (None, 'wait' | 'limit')."""
        now = fields.Datetime.now()
        history = self.search([('user_id', '=', user.id)], order='create_date desc')
        if history and (now - history[0].create_date).total_seconds() < RESEND_SECONDS:
            return None, 'wait'
        if len(history.filtered(lambda t: t.create_date > now - timedelta(days=1))) >= MAX_PER_DAY:
            return None, 'limit'
        history.write({'revoked': True})
        raw = secrets.token_urlsafe(32)
        self.create({
            'user_id': user.id,
            'token_hash': _hash(raw),
            'expires_at': now + timedelta(hours=TOKEN_HOURS),
        })
        return raw, None

    @api.model
    def lookup(self, raw):
        rec = self.search([('token_hash', '=', _hash(raw)), ('revoked', '=', False)], limit=1)
        if rec and rec.expires_at >= fields.Datetime.now():
            return rec
        return self.browse()

    @api.model
    def consume(self, raw):
        """Activate the user once. Returns the user, or None if the token is bad."""
        rec = self.lookup(raw)
        if not rec:
            return None
        user = rec.user_id
        user.write({'active': True})
        company = user.company_id
        plan = company.hotel_plan_id
        if plan.code == 'free':
            company.trial_end_date = fields.Date.today() + timedelta(days=plan.trial_days or 3)
        rec.revoked = True
        return user

    @api.model
    def send_verification(self, user, base_url):
        """Return None on success, or 'wait' | 'limit' | 'failed'."""
        raw, problem = self.issue(user)
        if problem:
            return problem
        link = '%s/hotel/verify/%s' % (base_url.rstrip('/'), raw)
        sender = self.env['ir.config_parameter'].sudo().get_param('mail.default.from') or ''
        body = (
            '<div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;color:#0f172a">'
            '<h2>Confirm your email</h2>'
            '<p>Hi %s, welcome to Hotel Manager. Confirm your email to start the free trial for %s.</p>'
            '<p><a href="%s" style="display:inline-block;background:#4f46e5;color:#fff;'
            'padding:12px 22px;border-radius:10px;text-decoration:none;font-weight:bold">'
            'Confirm my email</a></p>'
            '<p style="color:#64748b">This link expires in %d hours. If you did not sign up, ignore this email.</p>'
            '</div>'
        ) % (escape(user.name), escape(user.company_id.name), link, TOKEN_HOURS)
        mail = self.env['mail.mail'].sudo().create({
            'subject': 'Confirm your email for Hotel Manager',
            'body_html': body,
            'email_to': user.email,
            'email_from': sender,
        })
        mail.send(raise_exception=False)
        return None if mail.state == 'sent' else 'failed'
