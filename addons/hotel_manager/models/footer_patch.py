from odoo import api, models

WA_LI = ('<li><i class="fa fa-whatsapp fa-fw me-2"/>'
         '<a href="https://wa.me/2348165212254?text=Hi%2C%20I%27d%20like%20to%20know%20more%20about%20Hotel%20Manager" '
         'target="_blank" rel="noopener">WhatsApp: +234 816 521 2254</a></li>')
PHONE_LI = '<li><i class="fa fa-phone fa-fw me-2"/><a href="tel:+2348165212254">+234 816 521 2254</a></li>'
COPY_NEW = ('<span class="o_footer_copyright_name me-2">'
            '&amp;copy; <t t-out="datetime.date.today().year"/> Swift Digital Services. All rights reserved.</span>')


class ResCompany(models.Model):
    _inherit = 'res.company'

    @api.model
    def _hotel_patch_footer(self):
        View = self.env['ir.ui.view'].sudo()

        copy_view = View.search([('key', '=', 'website.footer_copyright_company_name')], limit=1)
        if copy_view and 'Swift Digital Services. All rights' not in copy_view.arch_db:
            arch = copy_view.arch_db
            start = arch.find('<span class="o_footer_copyright_name')
            end = arch.find('</span>', start)
            if start != -1 and end != -1:
                copy_view.write({'arch_db': arch[:start] + COPY_NEW + arch[end + len('</span>'):]})

        footer = View.search([('key', '=', 'website.footer_custom')], limit=1)
        if footer and 'wa.me/' not in footer.arch_db and PHONE_LI in footer.arch_db:
            footer.write({'arch_db': footer.arch_db.replace(PHONE_LI, PHONE_LI + '\n' + WA_LI, 1)})
