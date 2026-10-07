/** @odoo-module **/

import { onWillRender, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import { listView } from "@web/views/list/list_view";

const { DateTime } = luxon;

const TEXT_TYPES = ["char", "text", "html", "many2one", "many2many", "one2many"];
const NUMBER_TYPES = ["integer", "float", "monetary"];
const DATE_TYPES = ["date", "datetime"];

/**
 * List renderer with a per-column filter row under the column headers
 * (text box / dropdown / date range per column). Opt in per list with
 * js_class="otm_colsearch_list". Every box feeds the normal search model as
 * a hidden filter, so it combines with the search bar, group by, export,
 * pager and "select all" exactly like a typed search would.
 */
export class OtmColSearchListRenderer extends ListRenderer {
    static template = "otm_b2b_marketing.ColSearchListRenderer";

    setup() {
        super.setup();
        this.colFilters = useState({});
        this.colFilterIds = {};
        onWillRender(() => this._syncWithSearchModel());
    }

    // Forget a box's text when its hidden filter was removed from outside
    // (e.g. the user cleared the search bar).
    _syncWithSearchModel() {
        const sm = this.env.searchModel;
        if (!sm) {
            return;
        }
        const live = new Set(sm.query.map((q) => q.searchItemId));
        for (const name of Object.keys(this.colFilterIds)) {
            if (!live.has(this.colFilterIds[name])) {
                delete this.colFilterIds[name];
                delete this.colFilters[name];
            }
        }
    }

    getColSearch(column) {
        if (column.type !== "field" || !this.env.searchModel) {
            return null;
        }
        const field = this.props.list.fields[column.name];
        if (!field || field.searchable === false) {
            return null;
        }
        const value = this.colFilters[column.name] || {};
        if (field.type === "selection") {
            return { kind: "select", options: field.selection || [], value: value.value || "" };
        }
        if (field.type === "boolean") {
            return {
                kind: "select",
                options: [["1", "Yes"], ["0", "No"]],
                value: value.value || "",
            };
        }
        if (DATE_TYPES.includes(field.type)) {
            return { kind: "date", from: value.from || "", to: value.to || "" };
        }
        if (TEXT_TYPES.includes(field.type) || NUMBER_TYPES.includes(field.type)) {
            return { kind: "text", value: value.value || "" };
        }
        return null;
    }

    _buildDomain(name, field, value) {
        const domain = [];
        const v = (value.value || "").trim();
        if (field.type === "selection" && v) {
            domain.push([name, "=", v]);
        } else if (field.type === "boolean" && v) {
            domain.push([name, "=", v === "1"]);
        } else if (NUMBER_TYPES.includes(field.type) && v) {
            const num = Number(v);
            if (!Number.isNaN(num)) {
                domain.push([name, "=", num]);
            }
        } else if (TEXT_TYPES.includes(field.type) && v) {
            domain.push([name, "ilike", v]);
        } else if (DATE_TYPES.includes(field.type)) {
            const isDt = field.type === "datetime";
            if (value.from) {
                const d = DateTime.fromISO(value.from);
                domain.push([name, ">=", isDt ? this._utc(d.startOf("day")) : value.from]);
            }
            if (value.to) {
                const d = DateTime.fromISO(value.to);
                domain.push([name, "<=", isDt ? this._utc(d.endOf("day")) : value.to]);
            }
        }
        return domain;
    }

    _utc(dt) {
        return dt.toUTC().toFormat("yyyy-LL-dd HH:mm:ss");
    }

    onColSearchChange(column, key, rawValue) {
        const sm = this.env.searchModel;
        const name = column.name;
        const field = this.props.list.fields[name];
        const value = { ...(this.colFilters[name] || {}), [key]: rawValue };
        const domain = this._buildDomain(name, field, value);

        // Drop this column's previous hidden filter, if any.
        const prevId = this.colFilterIds[name];
        if (prevId !== undefined) {
            sm.query = sm.query.filter((q) => q.searchItemId !== prevId);
            delete sm.searchItems[prevId];
            delete this.colFilterIds[name];
        }
        if (domain.length) {
            this.colFilters[name] = value;
            const newId = sm.nextId;
            sm.createNewFilters([{ description: `${column.label}`, domain, invisible: "True" }]);
            this.colFilterIds[name] = newId;
        } else {
            delete this.colFilters[name];
            sm._notify();
        }
    }
}

registry.category("views").add("otm_colsearch_list", {
    ...listView,
    Renderer: OtmColSearchListRenderer,
});
