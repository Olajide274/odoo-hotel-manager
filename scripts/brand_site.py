import base64
from lxml import etree
P = '/mnt/extra-addons/hotel_manager/static/src/img/'
logo = base64.b64encode(open(P + 'swift_logo.svg', 'rb').read())
C = env['res.company']
vals = {
    'name': 'Swift Digital Services',
    'email': 'swiftdigitalservices00@gmail.com',
    'phone': '+234 816 521 2254',
    'website': 'https://swift-digital-services.vercel.app',
    'country_id': env.ref('base.ng').id,
}
ngn = env.ref('base.NGN', raise_if_not_found=False)
if ngn:
    vals['currency_id'] = ngn.id
for f, u in (('social_github', 'https://github.com/Olajide274'),
             ('social_linkedin', 'https://www.linkedin.com/in/michael-olajide-david-b27859383')):
    if f in C._fields:
        vals[f] = u
sw = C.search([('name', '=', 'Swift Digital Services')], limit=1)
if sw:
    sw.write(vals)
else:
    sw = C.create(vals)
try:
    sw.logo = logo
except Exception as e:
    print("RES company logo skipped:", str(e)[:100])
for u in env['res.users'].search([]):
    if u.has_group('base.group_system'):
        u.write({'company_ids': [(4, sw.id)]})
w = env['website'].search([], limit=1)
w.write({'name': 'Swift Digital Services', 'company_id': sw.id, 'logo': logo})

V = env['ir.ui.view'].with_context(active_test=False)
for v in V.search([('type', '=', 'qweb'), ('key', 'like', 'website.%header%')]):
    a = v.arch_db or ''
    n = a.replace('Contact Us', 'Start free trial').replace('href="/contactus"', 'href="/hotel/signup"')
    if n != a:
        v.arch_db = n
        print("RES header patched:", v.key)

FOOT = """<section class="sw-footer s_text_block pt48 pb24" data-snippet="s_text_block" data-name="Text">
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
<li><i class="fa fa-envelope fa-fw me-2"></i><a href="mailto:swiftdigitalservices00@gmail.com">swiftdigitalservices00@gmail.com</a></li>
<li><i class="fa fa-phone fa-fw me-2"></i><a href="tel:+2348165212254">+234 816 521 2254</a></li>
<li><i class="fa fa-globe fa-fw me-2"></i><a href="https://swift-digital-services.vercel.app" target="_blank" rel="noopener">swift-digital-services.vercel.app</a></li>
</ul>
<div class="sw-social mt-3">
<a href="https://github.com/Olajide274" target="_blank" rel="noopener" aria-label="GitHub"><i class="fa fa-github"></i></a>
<a href="https://www.linkedin.com/in/michael-olajide-david-b27859383" target="_blank" rel="noopener" aria-label="LinkedIn"><i class="fa fa-linkedin"></i></a>
<a href="mailto:swiftdigitalservices00@gmail.com" aria-label="Email"><i class="fa fa-envelope"></i></a>
</div>
</div>
</div></div></section>"""
views = V.search([('key', '=', 'website.footer_custom')])
if not views:
    views = V.search([('type', '=', 'qweb'), ('key', 'like', 'website.%')]).filtered(lambda v: 'Useful Links' in (v.arch_db or ''))
done = 0
for v in views:
    root = etree.fromstring(v.arch_db.encode())
    found = root.xpath("//*[@id='footer']")
    if not found:
        print("RES footer skipped (no #footer):", v.key)
        continue
    box = found[0]
    for ch in list(box):
        box.remove(ch)
    box.text = None
    box.append(etree.fromstring(FOOT))
    v.arch_db = etree.tostring(root, encoding='unicode')
    done += 1
print("RES footer views updated:", done)

bp = env.ref('website.brand_promotion', raise_if_not_found=False)
if bp:
    bp.active = False
env['ir.config_parameter'].sudo().set_param('auth_signup.invitation_scope', 'b2b')
env.cr.commit()
print("RES website:", w.name, "| company:", w.company_id.name, "| phone:", w.company_id.phone)
