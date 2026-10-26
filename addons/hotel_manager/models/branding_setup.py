import base64
from odoo import api, models
from odoo.modules.module import get_module_resource

PHONE = '+234 816 521 2254'
NAME = 'Swift Digital Services'

HEADER_CTA = """<data inherit_id="website.placeholder_header_call_to_action" name="Header Call to Action" active="True">
    <xpath expr="." position="inside">
        <li t-attf-class="#{_item_class}">
            <div t-attf-class="oe_structure oe_structure_solo #{_div_class}">
                <section class="oe_unremovable oe_unmovable s_text_block" data-snippet="s_text_block" data-name="Text">
                    <div class="container">
                        <a t-if="request.env.user._is_public()" href="/hotel/signup" class="oe_unremovable btn btn-primary btn_cta">Start free trial</a>
                        <a t-else="" href="/odoo" class="oe_unremovable btn btn-primary btn_cta">Open dashboard</a>
                    </div>
                </section>
            </div>
        </li>
    </xpath>
</data>"""

FOOTER = """<data inherit_id="website.layout" name="Default" active="True">
    <xpath expr="//div[@id='footer']" position="replace">
        <div id="footer" class="oe_structure oe_structure_solo" t-ignore="true" t-if="not no_footer"><section class="sw-footer s_text_block pt48 pb24" data-snippet="s_text_block" data-name="Text">
<div class="container"><div class="row g-4">
<div class="col-lg-4">
<img src="/hotel_manager/static/src/img/swift_logo_light.svg" alt="Swift Digital Services" height="46" class="mb-3"/>
<p>We build websites and software for businesses, from scoping to deployment. This hotel management platform is one of our products.</p>
</div>
<div class="col-6 col-lg-3 offset-lg-1">
<h5>Platform</h5>
<ul><li><a href="/hotel/pricing">Pricing</a></li><li><a href="/hotel/signup">Start free trial</a></li><li><a href="/web/login">Log in</a></li></ul>
</div>
<div class="col-6 col-lg-4">
<h5>Contact us</h5>
<ul>
<li><i class="fa fa-envelope fa-fw me-2"/><a href="mailto:swiftdigitalservices00@gmail.com">swiftdigitalservices00@gmail.com</a></li>
<li><i class="fa fa-phone fa-fw me-2"/><a href="tel:+2348165212254">+234 816 521 2254</a></li>
<li><i class="fa fa-whatsapp fa-fw me-2"/><a href="https://wa.me/2348165212254?text=Hi%2C%20I%27d%20like%20to%20know%20more%20about%20Hotel%20Manager" target="_blank" rel="noopener">WhatsApp: +234 816 521 2254</a></li>
<li><i class="fa fa-globe fa-fw me-2"/><a href="https://swift-digital-services.vercel.app" target="_blank" rel="noopener">swift-digital-services.vercel.app</a></li>
</ul>
<div class="sw-social mt-3">
<a href="https://github.com/Olajide274" target="_blank" rel="noopener" aria-label="GitHub"><i class="fa fa-github"/></a>
<a href="https://www.linkedin.com/in/michael-olajide-david-b27859383" target="_blank" rel="noopener" aria-label="LinkedIn"><i class="fa fa-linkedin"/></a>
<a href="mailto:swiftdigitalservices00@gmail.com" aria-label="Email"><i class="fa fa-envelope"/></a>
</div>
</div>
</div></div></section></div>
    </xpath>
</data>"""


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _hotel_setup_branding(self):
        env = self.env
        View = env['ir.ui.view'].sudo()
        website = env['website'].sudo().search([], limit=1)
        if not website:
            return
        website.company_id.sudo().write({'name': NAME, 'phone': PHONE})
        website.write({'name': NAME, 'homepage_url': '/hotel/pricing'})

        for key, arch in (('website.header_call_to_action', HEADER_CTA),
                          ('website.footer_custom', FOOTER)):
            view = View.search([('key', '=', key)], limit=1)
            if view and view.arch_db != arch:
                view.write({'arch_db': arch})

        # logo: first file that exists
        for fname in ('swift_logo.svg', 'swift_logo_dark.svg', 'logo.svg', 'logo.png'):
            path = get_module_resource('hotel_manager', 'static/src/img', fname)
            if path:
                with open(path, 'rb') as f:
                    website.write({'logo': base64.b64encode(f.read())})
                break

        # menus
        Menu = env['website.menu'].sudo()
        top = website.menu_id
        Menu.search([('parent_id', '=', top.id), ('url', 'in', ['/', '/contactus'])]).unlink()
        if not Menu.search([('parent_id', '=', top.id), ('url', '=', '/hotel/pricing')]):
            Menu.create({'name': 'Pricing', 'url': '/hotel/pricing',
                         'parent_id': top.id, 'website_id': website.id, 'sequence': 10})
        mine = Menu.search([('parent_id', '=', top.id), ('url', '=', '/odoo')], limit=1)
        if not mine:
            mine = Menu.create({'name': 'My Hotel', 'url': '/odoo', 'parent_id': top.id,
                                'website_id': website.id, 'sequence': 20})
        mine.write({'group_ids': [(4, env.ref('base.group_user').id)]})
