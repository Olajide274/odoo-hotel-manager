import re
V = env['ir.ui.view'].with_context(active_test=False)
PH = re.compile(r'\+1 555-555-\d{4}')
n = 0
for v in V.search([('type', '=', 'qweb')]):
    a = v.arch_db or ''
    if '555-555' not in a and 'yourcompany.example.com' not in a:
        continue
    b = re.sub(r'tel:\+1 555-555-\d{4}', 'tel:+2348165212254', a)
    b = PH.sub('+234 816 521 2254', b)
    b = b.replace('info@yourcompany.example.com', 'swiftdigitalservices00@gmail.com')
    if b != a:
        v.arch_db = b
        n += 1
        print("RES patched:", v.key or v.name)
env.cr.commit()
print("RES views patched:", n)
