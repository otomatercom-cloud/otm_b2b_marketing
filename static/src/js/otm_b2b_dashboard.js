/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { Component, onWillStart, useState } from "@odoo/owl";

export class OtmB2bDashboard extends Component {
    static template = "otm_b2b_marketing.Dashboard";
    // Odoo 19 enforces strict prop validation on OWL components (Rule 10);
    // this is a client-action root with no incoming props.
    static props = ["*"];

    setup() {
        this.orm = useService("orm");
        this.action = useService("action");
        this.state = useState({
            cards: {
                today_visits: 0,
                upcoming_visits: 0,
                completed_visits: 0,
                pending_visits: 0,
                institutions_assigned: 0,
                total_institutions: 0,
                new_institutions: 0,
                inactive_institutions: 0,
                leads_collected: 0,
                seminars_conducted: 0,
                mou_signed: 0,
            },
            byType: [],
            byDistrict: [],
            upcomingVisits: [],
            isManager: true,
            userName: "",
            loading: true,
        });

        onWillStart(async () => this.loadDashboard());
    }

    async loadDashboard() {
        this.state.loading = true;
        // All scoping (Marketing Executive sees only their own institutions
        // and visits; Manager/Head see everything) happens server-side in
        // get_dashboard_data() so the access logic lives in one place and
        // isn't duplicated - or allowed to drift - in the client.
        const data = await this.orm.call("otm.b2b.institution", "get_dashboard_data", []);
        Object.assign(this.state.cards, data.cards);
        this.state.byType = this._withBarPercent(data.by_type);
        this.state.byDistrict = this._withBarPercent(data.by_district);
        this.state.upcomingVisits = data.upcoming_visit_list;
        this.state.isManager = data.is_manager;
        this.state.userName = data.user_name;
        this.state.loading = false;
    }

    _withBarPercent(rows) {
        const max = rows.length ? Math.max(...rows.map((r) => r.count)) : 0;
        return rows.map((r) => ({
            ...r,
            pct: max ? Math.round((r.count * 100) / max) : 0,
        }));
    }

    openInstitutions() {
        this.action.doAction("otm_b2b_marketing.action_otm_b2b_institution");
    }

    openVisitPlans() {
        this.action.doAction("otm_b2b_marketing.action_otm_b2b_visit_plan");
    }

    openLeads() {
        this.action.doAction("otm_b2b_marketing.action_otm_b2b_lead");
    }

    openMou() {
        this.action.doAction("otm_b2b_marketing.action_otm_b2b_mou");
    }
}

registry.category("actions").add("otm_b2b_dashboard", OtmB2bDashboard);
