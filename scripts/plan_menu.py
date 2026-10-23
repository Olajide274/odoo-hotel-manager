menu = env['ir.ui.menu'].sudo().search([('name', '=', 'My Plan')])
act = env.ref('hotel_manager.action_my_plan_url', raise_if_not_found=False)
if not act:
    act = env['ir.actions.act_url'].sudo().create({'name': 'My Plan', 'url': '/hotel/my-plan', 'target': 'self'})
menu.write({'action': '%s,%d' % (act._name, act.id)})
env.cr.commit()
for m in menu:
    print("RES menu:", m.complete_name, "->", m.action._name, m.action.url, "| groups:", m.groups_id.mapped('full_name'))
