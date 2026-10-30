from odoo import http
from odoo.http import request


class HotelBookingBySlug(http.Controller):

    @http.route('/hotel/stay/<string:slug>', type='http', auth='public', website=True)
    def booking_page(self, slug, **kw):
        company = request.env['res.company'].sudo().search(
            [('hotel_booking_slug', '=', slug)], limit=1)
        if not company or company._hotel_trial_expired():
            return request.not_found()
        return request.render('hotel_manager.booking_form_template', {
            'rooms': company._hotel_public_rooms(),
            'error': kw.get('error'),
            'success': kw.get('success'),
        })
