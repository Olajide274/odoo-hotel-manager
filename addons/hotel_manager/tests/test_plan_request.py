from odoo.tests import tagged
from odoo.tests.common import TransactionCase


@tagged('post_install', '-at_install')
class TestPlanRequest(TransactionCase):

    def test_request_is_deduplicated_and_marked_done(self):
        free = self.env.ref('hotel_manager.plan_free')
        std = self.env.ref('hotel_manager.plan_standard')
        company = self.env['res.company'].create({'name': 'Req Hotel', 'hotel_plan_id': free.id})
        Req = self.env['hotel.plan.request']
        rec, created = Req.submit(company, std, self.env.user, '0800', 'hi')
        self.assertTrue(created)
        rec2, created2 = Req.submit(company, std, self.env.user, '0800', 'again')
        self.assertFalse(created2)
        self.assertEqual(rec, rec2)
        self.env['hotel.plan.activate'].create({
            'company_id': company.id, 'plan_id': std.id, 'days': 30}).action_activate()
        self.assertEqual(rec.state, 'done')

    def test_setup_fee_off_by_default(self):
        company = self.env['res.company'].create({'name': 'Fee Hotel'})
        self.assertFalse(company.hotel_charge_setup)
