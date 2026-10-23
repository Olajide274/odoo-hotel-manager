from datetime import timedelta

from odoo import api, fields, models


class HotelDashboard(models.AbstractModel):
    _name = 'hotel.dashboard'
    _description = 'Hotel Dashboard'

    @api.model
    def get_data(self):
        company = self.env.company
        today = fields.Date.context_today(self)
        Room = self.env['hotel.room'].sudo()
        Booking = self.env['hotel.booking'].sudo()
        cdom = [('company_id', '=', company.id)]

        rooms = Room.search(cdom)
        status = {s: 0 for s in ('available', 'occupied', 'cleaning', 'maintenance')}
        for r in rooms:
            status[r.status] = status.get(r.status, 0) + 1
        total = len(rooms)
        occupancy = round(status['occupied'] * 100.0 / total) if total else 0

        arrivals = Booking.search(cdom + [
            ('check_in', '=', today), ('state', 'in', ('draft', 'confirmed'))])
        departures = Booking.search(cdom + [
            ('check_out', '=', today), ('state', '=', 'checked_in')])
        in_house = Booking.search_count(cdom + [('state', '=', 'checked_in')])

        upcoming = Booking.search(cdom + [
            ('check_in', '>=', today), ('state', 'in', ('draft', 'confirmed'))],
            order='check_in asc, id asc', limit=5)

        month_start = today.replace(day=1)
        month_done = Booking.search(cdom + [
            ('state', '=', 'checked_out'),
            ('check_out', '>=', month_start), ('check_out', '<=', today)])
        month_value = sum(month_done.mapped('total_price'))

        collected = sum(b.total_price for b in month_done
                        if b.payment_state in ('paid', 'in_payment'))
        unpaid = Booking.search(cdom + [
            ('invoice_id', '!=', False), ('state', '!=', 'cancelled'),
            ('payment_state', 'in', ('not_paid', 'partial'))])
        outstanding = sum(unpaid.mapped('invoice_id.amount_residual'))

        plan = company.hotel_plan_id
        full_reports = (not plan) or plan.has_full_reports
        trend = []
        if full_reports:
            for i in range(6, -1, -1):
                day = today - timedelta(days=i)
                count = Booking.search_count(cdom + [
                    ('check_in', '=', day), ('state', '!=', 'cancelled')])
                trend.append({'label': day.strftime('%a'), 'count': count})

        return {
            'hotel': company.name,
            'symbol': company.currency_id.symbol or '',
            'today': fields.Date.to_string(today),
            'rooms_total': total,
            'status': status,
            'occupancy': occupancy,
            'arrivals': len(arrivals),
            'departures': len(departures),
            'in_house': in_house,
            'month_value': month_value,
            'month_stays': len(month_done),
            'collected': collected,
            'outstanding': outstanding,
            'outstanding_count': len(unpaid),
            'full_reports': full_reports,
            'trend': trend,
            'upcoming': [{
                'name': b.name, 'guest': b.guest_name,
                'room': b.room_id.name, 'check_in': fields.Date.to_string(b.check_in),
                'nights': b.nights,
            } for b in upcoming],
        }
