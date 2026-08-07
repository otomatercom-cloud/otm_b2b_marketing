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
        this.notification = useService("notification");
        this.state = useState({
            cards: {
                today_visits: 0,
                upcoming_visits: 0,
                completed_visits: 0,
                pending_visits: 0,
                live_visits: 0,
                today_completed: 0,
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
            liveVisits: [],
            todayCompleted: [],
            territoryPerformance: [],
            myInstitutions: [],
            mySeminars: [],
            allSeminarsPlanned: [],
            isManager: true,
            userName: "",
            telegramConnected: false,
            telegramDeepLink: false,
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
        this.state.liveVisits = data.live_visit_list;
        this.state.todayCompleted = data.today_completed_list;
        this.state.territoryPerformance = data.territory_performance;
        this.state.myInstitutions = data.my_institutions;
        this.state.mySeminars = data.my_seminars;
        this.state.allSeminarsPlanned = data.all_seminars_planned;
        this.state.isManager = data.is_manager;
        this.state.userName = data.user_name;
        this.state.telegramConnected = data.telegram_connected;
        this.state.telegramDeepLink = data.telegram_deep_link;
        this.state.loading = false;
    }

    connectTelegram() {
        if (this.state.telegramDeepLink) {
            window.open(this.state.telegramDeepLink, "_blank");
            this.notification.add(
                "Opened Telegram. Tap Start in the chat to finish connecting - this dashboard " +
                "will show you as connected once you do.",
                { type: "info", sticky: true }
            );
        } else {
            this.notification.add(
                "Telegram isn't set up yet - ask your admin to configure the bot under " +
                "B2B Marketing > Configuration > Telegram Settings.",
                { type: "warning" }
            );
        }
    }

    async disconnectTelegram() {
        await this.orm.call("res.users", "action_disconnect_telegram_self", []);
        this.notification.add("Telegram disconnected. You'll no longer receive messages here.", {
            type: "info",
        });
        await this.loadDashboard();
    }

    _withBarPercent(rows) {
        const max = rows.length ? Math.max(...rows.map((r) => r.count)) : 0;
        return rows.map((r) => ({
            ...r,
            pct: max ? Math.round((r.count * 100) / max) : 0,
        }));
    }

    _getLocation() {
        // Best-effort GPS capture - never blocks check-in if there's no
        // location available. Two sources, in priority order:
        // 1. window.otmB2BLocation - set by a native app wrapper (e.g. a
        //    Kodular WebViewer) via RunJavaScript, using the phone's own
        //    Location Sensor. Stock Android WebViews often don't support
        //    navigator.geolocation at all (no permission plumbing without
        //    a custom WebChromeClient), so a wrapper app feeding real GPS
        //    in directly is the reliable path for that case.
        // 2. navigator.geolocation - the normal browser API, used when
        //    running in an actual browser (not a bare WebView).
        return new Promise((resolve) => {
            if (window.otmB2BLocation && window.otmB2BLocation.latitude) {
                resolve(window.otmB2BLocation);
                return;
            }
            if (!navigator.geolocation) {
                resolve(null);
                return;
            }
            navigator.geolocation.getCurrentPosition(
                (pos) => resolve({ latitude: pos.coords.latitude, longitude: pos.coords.longitude }),
                () => resolve(null),
                { timeout: 8000, maximumAge: 60000 }
            );
        });
    }

    async checkIn(planId) {
        const loc = await this._getLocation();
        const result = await this.orm.call("otm.b2b.visit.plan", "action_dashboard_check_in", [planId], {
            latitude: loc ? loc.latitude : null,
            longitude: loc ? loc.longitude : null,
        });
        this.notification.add(`Checked in at ${result.institution}.`, { type: "success" });
        await this.loadDashboard();
    }

    async checkOut(visit) {
        await this.orm.call("otm.b2b.visit.record", "action_check_out", [visit.id]);

        if (visit.portal_url) {
            window.open(visit.portal_url, "_blank");
            this.notification.add(
                `Checked out of ${visit.institution}. Complete the visit update in the new tab.`,
                { type: "success" }
            );
        } else {
            this.notification.add("Checked out.", { type: "success" });
        }

        await this.loadDashboard();
    }

    async checkInSeminar(planId) {
        const result = await this.orm.call("otm.b2b.seminar.plan", "action_dashboard_check_in", [planId]);
        this.notification.add(`Checked in for seminar at ${result.institution}.`, { type: "success" });
        await this.loadDashboard();
    }

    async checkOutSeminar(seminar) {
        await this.orm.call("otm.b2b.seminar", "action_check_out", [seminar.id]);

        if (seminar.portal_url) {
            window.open(seminar.portal_url, "_blank");
            this.notification.add(
                `Checked out of the seminar at ${seminar.institution}. Complete the update in the new tab.`,
                { type: "success" }
            );
        } else {
            this.notification.add("Checked out.", { type: "success" });
        }

        await this.loadDashboard();
    }

    openSeminarRecord(seminarId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "otm.b2b.seminar",
            res_id: seminarId,
            view_mode: "form",
            views: [[false, "form"]],
        });
    }

    openSeminarPlanRecord(planId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "otm.b2b.seminar.plan",
            res_id: planId,
            view_mode: "form",
            views: [[false, "form"]],
        });
    }

    openVisitRecord(visitId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "otm.b2b.visit.record",
            res_id: visitId,
            view_mode: "form",
            views: [[false, "form"]],
        });
    }

    openInstitutions() {
        this.action.doAction("otm_b2b_marketing.action_otm_b2b_institution");
    }

    openVisitPlans() {
        this.action.doAction("otm_b2b_marketing.action_otm_b2b_visit_plan");
    }

    openSeminars() {
        this.action.doAction("otm_b2b_marketing.action_otm_b2b_seminar_plan");
    }

    openLeads() {
        this.action.doAction("otm_b2b_marketing.action_otm_b2b_lead");
    }

    openMou() {
        this.action.doAction("otm_b2b_marketing.action_otm_b2b_mou");
    }
}

registry.category("actions").add("otm_b2b_dashboard", OtmB2bDashboard);
