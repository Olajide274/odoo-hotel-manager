/** @odoo-module **/
import { registry } from "@web/core/registry";
import { Component, onWillStart, useState } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class HotelDashboard extends Component {
    static template = "hotel_manager.Dashboard";

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({ loading: true, d: {} });
        onWillStart(async () => {
            this.state.d = await this.orm.call("hotel.dashboard", "get_data", []);
            this.state.loading = false;
        });
    }

    money(v) {
        return this.state.d.symbol + Math.round(v || 0).toLocaleString("en-US");
    }

    barHeight(count) {
        const max = Math.max(1, ...this.state.d.trend.map((t) => t.count));
        return Math.max(6, Math.round((count / max) * 100));
    }

    newBooking() {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "hotel.booking",
            views: [[false, "form"]],
            target: "current",
        });
    }
    openBookings() { this.action.doAction("hotel_manager.hotel_booking_action"); }
    openRooms() { this.action.doAction("hotel_manager.hotel_room_action"); }
}

registry.category("actions").add("hotel_dashboard", HotelDashboard);
