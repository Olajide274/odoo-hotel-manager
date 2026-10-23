from odoo import api, models

# Standard Odoo root menus that hotel users should not see
_RESTRICTED = {
    'base.menu_management': ['base.group_system'],                      # Apps
    'spreadsheet_dashboard.spreadsheet_dashboard_menu_root': ['base.group_system'],  # Dashboards
    'mail.menu_root_discuss': ['base.group_system'],                    # Discuss
    'account.menu_finance': ['base.group_system', 'account.group_account_manager'],  # Invoicing
}


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _hotel_restrict_menus(self):
        Menu = self.env['ir.ui.menu'].sudo()
        field = 'groups_id' if 'groups_id' in Menu._fields else 'group_ids'
        for menu_xmlid, group_xmlids in _RESTRICTED.items():
            menu = self.env.ref(menu_xmlid, raise_if_not_found=False)
            if not menu:
                continue
            groups = self.env['res.groups']
            for gx in group_xmlids:
                groups |= self.env.ref(gx, raise_if_not_found=False) or groups.browse()
            if groups:
                menu.sudo().write({field: [(6, 0, groups.ids)]})
