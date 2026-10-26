from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestSingleDevice(TransactionCase):

    def _user(self, login, admin=False):
        groups = [self.env.ref('base.group_user').id]
        if admin:
            groups.append(self.env.ref('base.group_system').id)
        return self.env['res.users'].with_context(no_reset_password=True).create({
            'name': login, 'login': login, 'email': login,
            'groups_id': [(6, 0, groups)]})

    def test_new_login_invalidates_old_session(self):
        user = self._user('sd_staff@test.com')
        self.env.flush_all()
        before = user._compute_session_token('sid-1')
        user._hotel_rotate_session_key()
        self.env.flush_all()
        self.env.registry.clear_cache()
        after = user._compute_session_token('sid-1')
        self.assertNotEqual(before, after)

    def test_admin_is_exempt(self):
        admin = self._user('sd_admin@test.com', admin=True)
        self.env.flush_all()
        before = admin._compute_session_token('sid-1')
        admin._hotel_rotate_session_key()
        self.env.flush_all()
        self.env.registry.clear_cache()
        self.assertFalse(admin.hotel_session_key)
        self.assertEqual(before, admin._compute_session_token('sid-1'))
