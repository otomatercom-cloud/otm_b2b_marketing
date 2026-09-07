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
                total_institutions: 0,
                new_institutions: 0,
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
        // Best-effort GPS capture - never blocks check-in/check-out if
        // there's no location available, but tries hard to actually get
        // one first, AND reports back WHY it failed rather than just
        // silently returning nothing. That "why" is what's been missing
        // this whole time - "not captured" alone can mean permission
        // denied, no GPS fix in time, or the API being unavailable, and
        // those need completely different fixes. Returns
        // { location: {latitude, longitude} | null, error: string | null }.
        //
        // Two sources, in priority order:
        // 1. window.otmB2BLocation - set by a native app wrapper (e.g. a
        //    Kodular WebViewer) via RunJavaScript, using the phone's own
        //    Location Sensor. Stock Android WebViews often don't support
        //    navigator.geolocation at all (no permission plumbing without
        //    a custom WebChromeClient), so a wrapper app feeding real GPS
        //    in directly is the reliable path for that case.
        // 2. navigator.geolocation - the normal browser API, used when
        //    running in an actual browser (not a bare WebView).
        const ERROR_NAMES = { 1: "Permission denied", 2: "Position unavailable", 3: "Timed out" };

        const tryOnce = (options) => new Promise((resolve) => {
            navigator.geolocation.getCurrentPosition(
                (pos) => resolve({ location: { latitude: pos.coords.latitude, longitude: pos.coords.longitude }, error: null }),
                (err) => resolve({ location: null, error: ERROR_NAMES[err.code] || err.message || "Unknown error" }),
                options
            );
        });

        return new Promise(async (resolve) => {
            if (window.otmB2BLocation && window.otmB2BLocation.latitude) {
                resolve({ location: window.otmB2BLocation, error: null });
                return;
            }
            if (!navigator.geolocation) {
                resolve({ location: null, error: "Geolocation not available in this browser/app" });
                return;
            }
            const options = { enableHighAccuracy: true, timeout: 20000, maximumAge: 30000 };
            let result = await tryOnce(options);
            if (!result.location) {
                result = await tryOnce(options);
            }
            resolve(result);
        });
    }

    async checkIn(planId) {
        const { location, error } = await this._getLocation();
        if (!location) {
            this.notification.add(
                `Check-in requires location access. ${error}. Please enable location for this site ` +
                `and try again.`,
                { type: "danger", sticky: true }
            );
            return;
        }
        const result = await this.orm.call("otm.b2b.visit.plan", "action_dashboard_check_in", [planId], {
            latitude: location.latitude,
            longitude: location.longitude,
        });
        this.notification.add(`Checked in at ${result.institution}.`, { type: "success" });
        await this.loadDashboard();
    }

    async checkOut(visit) {
        const { location, error } = await this._getLocation();
        await this.orm.call("otm.b2b.visit.record", "action_check_out", [visit.id], {
            latitude: location ? location.latitude : null,
            longitude: location ? location.longitude : null,
        });

        if (!location) {
            this.notification.add(`Location not captured: ${error}`, { type: "warning" });
        }

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
        const { location, error } = await this._getLocation();
        if (!location) {
            this.notification.add(
                `Check-in requires location access. ${error}. Please enable location for this site ` +
                `and try again.`,
                { type: "danger", sticky: true }
            );
            return;
        }
        const result = await this.orm.call("otm.b2b.seminar.plan", "action_dashboard_check_in", [planId], {
            latitude: location.latitude,
            longitude: location.longitude,
        });
        this.notification.add(`Checked in for seminar at ${result.institution}.`, { type: "success" });
        await this.loadDashboard();
    }

    async checkOutSeminar(seminar) {
        const { location, error } = await this._getLocation();
        await this.orm.call("otm.b2b.seminar", "action_check_out", [seminar.id], {
            latitude: location ? location.latitude : null,
            longitude: location ? location.longitude : null,
        });

        if (!location) {
            this.notification.add(`Location not captured: ${error}`, { type: "warning" });
        }

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

    openInstitutionRecord(institutionId) {
        this.action.doAction({
            type: "ir.actions.act_window",
            res_model: "otm.b2b.institution",
            res_id: institutionId,
            view_mode: "form",
            views: [[false, "form"]],
        });
    }

    openInstitutions() {
        this.action.doAction("otm_b2b_marketing.action_otm_b2b_institution");
    }

    openFiltered(model, name, domain, context) {
        this.action.doAction({
            type: "ir.actions.act_window",
            name: name,
            res_model: model,
            view_mode: "list,form",
            views: [[false, "list"], [false, "form"]],
            domain: domain || [],
            context: context || {},
        });
    }

    async openNearbyInstitutions() {
        const { location, error } = await this._getLocation();
        if (!location) {
            this.notification.add(`Couldn't get your location: ${error}`, { type: "warning" });
            return;
        }
        const result = await this.orm.call("otm.b2b.institution", "action_find_nearby", [
            location.latitude, location.longitude, 20,
        ]);
        if (!result.count) {
            this.notification.add("No institutions with GPS data found within 20km of you.", { type: "info" });
            return;
        }
        // Institution list already has a Total Visits column, so "how
        // many times visited" is right there without building a
        // separate view - just filter it down to the nearby set,
        // already sorted nearest-first by the backend.
        this.openFiltered("otm.b2b.institution", `Institutions Within 20km (${result.count})`, [["id", "in", result.ids]]);
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
