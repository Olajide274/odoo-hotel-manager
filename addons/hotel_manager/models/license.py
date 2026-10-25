import base64
import hashlib
import hmac
import json
import math
import os
import uuid
from datetime import datetime, timedelta

from odoo import api, fields, models
from odoo.exceptions import AccessError, UserError

TRIAL_DAYS = 3

PACKAGES = {
    'trial': {'label': 'Free Trial', 'max_rooms': 5,
              'features': {'bookings'}},
    'starter': {'label': 'Starter', 'max_rooms': 10,
                'features': {'bookings'}},
    'pro': {'label': 'Pro', 'max_rooms': 30,
            'features': {'bookings', 'billing', 'reports'}},
    'business': {'label': 'Business', 'max_rooms': None,
                 'features': {'bookings', 'billing', 'reports', 'website'}},
}

FEATURE_LABELS = {
    'bookings': 'Bookings and check-in/out',
    'billing': 'Extra charges and invoicing',
    'reports': 'Reports and dashboard',
    'website': 'Website booking and Paystack',
}


def make_activation_code(secret, install_id, package, expires):
    payload = {
        'v': 1,
        'install_id': install_id,
        'package': package,
        'expires': expires.replace(microsecond=0).isoformat(),
    }
    body = base64.urlsafe_b64encode(
        json.dumps(payload, sort_keys=True).encode()).decode().rstrip('=')
    signature = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
    return f'{body}.{signature}'


class HotelLicense(models.Model):
    _name = 'hotel.license'
    _description = 'Hotel License'
    _rec_name = 'install_id'
    _sql_constraints = [('company_uniq', 'unique(company_id)', 'One licence per hotel.')]

    company_id = fields.Many2one(
        'res.company', required=True, index=True, ondelete='cascade', readonly=True,
        default=lambda self: self.env.company)

    install_id = fields.Char(
        default=lambda self: str(uuid.uuid4()), readonly=True, copy=False)
    package = fields.Selection(
        [(key, val['label']) for key, val in PACKAGES.items()],
        default='trial', required=True, readonly=True)
    trial_start = fields.Datetime(default=fields.Datetime.now, readonly=True)
    expires_at = fields.Datetime(
        default=lambda self: fields.Datetime.now() + timedelta(days=TRIAL_DAYS),
        readonly=True)
    status = fields.Selection(
        [('active', 'Active'), ('expired', 'Expired')], compute='_compute_status')
    days_left = fields.Integer(compute='_compute_status')
    features_text = fields.Text(compute='_compute_features_text')

    @api.depends('expires_at')
    def _compute_status(self):
        now = fields.Datetime.now()
        for lic in self:
            if not lic.expires_at or lic.expires_at <= now:
                lic.status = 'expired'
                lic.days_left = 0
            else:
                lic.status = 'active'
                lic.days_left = math.ceil((lic.expires_at - now).total_seconds() / 86400)

    @api.depends('package')
    def _compute_features_text(self):
        for lic in self:
            pkg = PACKAGES[lic.package]
            rooms = 'unlimited' if pkg['max_rooms'] is None else f"up to {pkg['max_rooms']}"
            included = ', '.join(
                label for key, label in FEATURE_LABELS.items() if key in pkg['features'])
            lic.features_text = f'Rooms: {rooms}\nIncluded: {included}'

    # ---------- access helpers ----------
    @api.model
    def _company(self, company=None):
        return (company or self.env.company).sudo()

    @api.model
    def _exempt(self, company=None):
        """A company with no plan (for example your own admin company) is never restricted."""
        return not self._company(company).hotel_plan_id

    @api.model
    def _current(self, company=None):
        company = self._company(company)
        lic = self.sudo().search([('company_id', '=', company.id)], limit=1)
        if not lic:
            lic = self.sudo().create({'company_id': company.id})
        return lic

    @api.model
    def _set_package(self, package, expires_at, company=None):
        lic = self._current(company)
        lic.write({'package': package, 'expires_at': expires_at})
        return lic

    @api.model
    def _grant(self, package, days=3650, company=None):
        return self._set_package(package, fields.Datetime.now() + timedelta(days=days), company)

    @api.model
    def has_feature(self, feature, company=None):
        if self._exempt(company):
            return True
        lic = self._current(company)
        return lic.status == 'active' and feature in PACKAGES[lic.package]['features']

    @api.model
    def assert_active(self, company=None):
        if self._exempt(company):
            return
        lic = self._current(company)
        if lic.status == 'expired':
            raise UserError(
                f"Your license expired on {lic.expires_at:%Y-%m-%d}. The system is "
                f"read-only until it is renewed. Contact support to activate a package.")

    @api.model
    def require(self, feature, company=None):
        if self._exempt(company):
            return True
        self.assert_active(company)
        lic = self._current(company)
        if feature in PACKAGES[lic.package]['features']:
            return True
        needed = next(
            (PACKAGES[key]['label'] for key in ('starter', 'pro', 'business')
             if feature in PACKAGES[key]['features']), 'a higher package')
        raise UserError(
            f"{FEATURE_LABELS.get(feature, feature)} is not included in your "
            f"{PACKAGES[lic.package]['label']} package. Upgrade to {needed} to use it.")

    @api.model
    def check_room_limit(self, adding=1, company=None):
        if self._exempt(company):
            return
        self.assert_active(company)
        lic = self._current(company)
        limit = PACKAGES[lic.package]['max_rooms']
        if limit is None:
            return
        current = self.env['hotel.room'].sudo().search_count(
            [('company_id', '=', self._company(company).id)])
        if current + adding > limit:
            raise UserError(
                f"Your {PACKAGES[lic.package]['label']} package allows up to {limit} "
                f"rooms. Upgrade to add more.")

    @api.model
    def notice(self, company=None):
        if self._exempt(company):
            return False
        lic = self._current(company)
        if lic.status == 'expired':
            return 'License expired. The system is read-only until you renew.'
        if lic.days_left <= 3:
            return f"{PACKAGES[lic.package]['label']} license: {lic.days_left} day(s) left."
        return False

    @api.model
    def action_open(self):
        lic = self._current()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Hotel License',
            'res_model': 'hotel.license',
            'res_id': lic.id,
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'current',
        }

    # ---------- activation ----------
    @api.model
    def activate_code(self, code):
        if not (self.env.su or self.env.user.has_group('hotel_manager.group_hotel_manager')):
            raise AccessError('Only a hotel manager can activate a license.')
        secret = os.environ.get('HOTEL_LICENSE_SECRET')
        if not secret:
            raise UserError('License activation is not configured on this server.')
        try:
            body, signature = (code or '').strip().split('.')
            expected = hmac.new(secret.encode(), body.encode(), hashlib.sha256).hexdigest()
            valid = hmac.compare_digest(signature, expected)
            payload = json.loads(base64.urlsafe_b64decode(body + '=' * (-len(body) % 4)))
            expires = datetime.fromisoformat(payload['expires'])
            package = payload['package']
            install_id = payload['install_id']
        except (ValueError, KeyError, TypeError):
            raise UserError('This activation code is not valid.')
        if not valid:
            raise UserError('This activation code is not valid.')
        lic = self._current()
        if install_id != lic.install_id:
            raise UserError('This activation code was issued for a different installation.')
        if package not in PACKAGES or package == 'trial':
            raise UserError('This activation code is not valid.')
        if expires <= fields.Datetime.now():
            raise UserError('This activation code has already expired.')
        return self._set_package(package, expires)


class HotelLicenseActivate(models.TransientModel):
    _name = 'hotel.license.activate'
    _description = 'Activate Hotel License'

    code = fields.Text(required=True)

    def action_activate(self):
        self.ensure_one()
        self.env['hotel.license'].activate_code(self.code)
        return {'type': 'ir.actions.client', 'tag': 'reload'}
