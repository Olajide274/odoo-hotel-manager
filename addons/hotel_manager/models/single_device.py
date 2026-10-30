import secrets

from odoo import SUPERUSER_ID, api, fields, models


class ResUsersSingleDevice(models.Model):
    _inherit = 'res.users'

    hotel_session_key = fields.Char(copy=False, readonly=True, prefetch=False)

    def _get_session_token_fields(self):
        return super()._get_session_token_fields() | {'hotel_session_key'}

    def _hotel_rotate_session_key(self):
        """New key = every older session of this user stops working.
        System administrators are exempt so you can stay logged in everywhere."""
        for user in self.sudo():
            if user.has_group('base.group_system'):
                continue
            user.write({'hotel_session_key': secrets.token_hex(16)})

    @classmethod
    def authenticate(cls, db, credential, user_agent_env):
        info = super().authenticate(db, credential, user_agent_env)
        uid = info.get('uid') if isinstance(info, dict) else None
        if uid:
            # own cursor, committed immediately, so the new key is saved
            with cls.pool.cursor() as cr:
                env = api.Environment(cr, SUPERUSER_ID, {})
                env['res.users'].browse(uid)._hotel_rotate_session_key()
        return info
