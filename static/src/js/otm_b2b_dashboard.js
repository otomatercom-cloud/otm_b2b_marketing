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
            availableExecutives: [],
            selectedExecutiveId: false,
            viewingOther: false,
            viewingExecutiveName: false,
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
        // and visits; Manager/Head see everything, or - if a manager has
        // picked one executive from the dropdown - just that executive's
        // data) happens server-side in get_dashboard_data() so the access
        // logic lives in one place and isn't duplicated - or allowed to
        // drift - in the client.
        const data = await this.orm.call("otm.b2b.institution", "get_dashboard_data", [
            this.state.selectedExecutiveId || false,
        ]);
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
        this.state.availableExecutives = data.available_executives;
        this.state.viewingOther = data.viewing_other;
        this.state.viewingExecutiveName = data.viewing_executive_name;
        this.state.isManager = data.is_manager;
        this.state.userName = data.user_name;
        this.state.telegramConnected = data.telegram_connected;
        this.state.telegramDeepLink = data.telegram_deep_link;
        this.state.loading = false;
    }

    onExecutiveFilterChange(ev) {
        const value = ev.target.value;
        this.state.selectedExecutiveId = value ? parseInt(value, 10) : false;
        this.loadDashboard();
    }

    // Domain leaf(s) scoping a click-through list to the currently
    // selected executive, if any - so drilling into a KPI card while
    // filtered stays filtered, instead of dumping the full team's
    // records. Returns [] (no extra filter) when no executive is picked.
    _execDomain(field) {
        if (!this.state.selectedExecutiveId) {
            return [];
        }
        return [[field, "=", this.state.selectedExecutiveId]];
    }

    _institutionExecDomain() {
        if (!this.state.selectedExecutiveId) {
            return [];
        }
        return ["|",
            ["marketing_manager_id", "=", this.state.selectedExecutiveId],
            ["user_id", "=", this.state.selectedExecutiveId],
        ];
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
            // Permission being granted doesn't guarantee a GPS fix -
            // indoors, underground, or a cold GPS chip can all still fail
            // or take too long. Try three times with progressively looser
            // requirements before giving up, instead of retrying the same
            // strict high-accuracy request twice:
            // 1. Fresh, high-accuracy (satellite) fix - best case.
            // 2. High-accuracy again, but now accept a fix the phone
            //    already has cached from the last minute - often
            //    resolves instantly if attempt 1 just needed more time.
            // 3. Low-accuracy (WiFi/cell-tower) fallback, which works
            //    indoors where GPS satellites can't be seen at all, and
            //    accepts anything cached in the last 5 minutes.
            const attempts = [
                { enableHighAccuracy: true, timeout: 15000, maximumAge: 0 },
                { enableHighAccuracy: true, timeout: 15000, maximumAge: 60000 },
                { enableHighAccuracy: false, timeout: 15000, maximumAge: 300000 },
            ];
            let result = { location: null, error: "Unknown error" };
            for (const options of attempts) {
                result = await tryOnce(options);
                if (result.location) {
                    break;
                }
            }
            resolve(result);
        });
    }

    // Permission being granted doesn't mean a fix will succeed, so the
    // message needs to differ: "Permission denied" is a settings problem,
    // everything else ("Position unavailable", "Timed out") is a signal
    // problem that moving somewhere with a clearer view of the sky (or
    // just near a window) usually fixes.
    _locationErrorMessage(error) {
        if (error === "Permission denied") {
            return `Check-in requires location access. Permission denied - please enable location ` +
                `for this site in your browser/app settings and try again.`;
        }
        return `Couldn't get a location fix (${error}). This usually happens indoors or ` +
            `underground - try moving near a window, outdoors, or somewhere with a clearer view ` +
            `of the sky, then try again.`;
    }

    async checkIn(planId) {
        const { location, error } = await this._getLocation();
        if (!location) {
            this.notification.add(this._locationErrorMessage(error), { type: "danger", sticky: true });
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
            this.notification.add(this._locationErrorMessage(error), { type: "danger", sticky: true });
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
        // Matches the "Total institutions" card exactly - the full
        // assigned set (including "New" ones), scoped to whichever
        // executive is currently selected in the filter (if any), so the
        // number on the card and what you see after clicking it agree.
        this.openFiltered("otm.b2b.institution", "Institutions", this._institutionExecDomain());
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
        this.openFiltered("otm.b2b.visit.plan", "Visit Planning", this._execDomain("user_id"));
    }

    openSeminars() {
        this.openFiltered("otm.b2b.seminar.plan", "Seminar Booking", this._execDomain("user_id"));
    }

    openLeads() {
        // Matches get_dashboard_data()'s lead_domain: assigned institution
        // OR directly collected by this person (their visit), so a lead
        // from an institution no longer assigned to them still shows up.
        this.openFiltered("otm.b2b.lead", "Leads Collected",
            this._execInstitutionLinkedDomain("visit_id.user_id"));
    }

    openMou() {
        this.openFiltered("otm.b2b.mou", "MOU Management", this._execInstitutionLinkedDomain());
    }

    openSeminarsConducted() {
        // Matches get_dashboard_data()'s seminar_domain: assigned
        // institution OR the seminar they personally conducted.
        this.openFiltered("otm.b2b.seminar", "Seminar Management",
            this._execInstitutionLinkedDomain("seminar_plan_id.user_id"));
    }

    // Same idea as _institutionExecDomain(), for models that don't carry
    // a direct user_id but link to Institution (Lead/Seminar/MOU) - filter
    // through institution_id.marketing_manager_id / institution_id.user_id,
    // optionally OR'd with a direct-attribution field path (e.g.
    // "visit_id.user_id") when the caller has one, matching the backend
    // dashboard scoping exactly.
    _execInstitutionLinkedDomain(directField) {
        if (!this.state.selectedExecutiveId) {
            return [];
        }
        const id = this.state.selectedExecutiveId;
        const institutionLeaves = ["|",
            ["institution_id.marketing_manager_id", "=", id],
            ["institution_id.user_id", "=", id],
        ];
        if (!directField) {
            return institutionLeaves;
        }
        return ["|", ...institutionLeaves, [directField, "=", id]];
    }
}

registry.category("actions").add("otm_b2b_dashboard", OtmB2bDashboard);
