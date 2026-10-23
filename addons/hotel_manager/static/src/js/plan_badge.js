/** @odoo-module **/
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { rpc } from "@web/core/network/rpc";

class HotelPlanBadge extends Component {
    static template = "hotel_manager.PlanBadge";
    setup() {
        this.state = useState({ label: "", css: "info", url: "/hotel/my-plan" });
        onWillStart(async () => {
            try {
                Object.assign(this.state, await rpc("/hotel/plan/status"));
            } catch (e) {
                /* no badge if the call fails */
            }
        });
    }
}

registry.category("systray").add("hotel_manager.plan_badge", { Component: HotelPlanBadge }, { sequence: 1 });
