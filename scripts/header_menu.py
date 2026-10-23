w = env['website'].search([], limit=1)
top = w.menu_id
M = env['website.menu']
if not M.search([('url', '=', '/odoo'), ('parent_id', '=', top.id)]):
    M.create({'name': 'My Hotel', 'url': '/odoo', 'parent_id': top.id, 'website_id': w.id, 'sequence': 40})
env['ir.attachment'].sudo().search([('url', 'like', '/web/assets/%')]).unlink()
env.cr.commit()
for m in M.search([('parent_id', '=', top.id)], order='sequence'):
    print("RES menu:", m.name, m.url)
