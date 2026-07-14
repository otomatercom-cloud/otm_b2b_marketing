# B2B Marketing - Logic School Of Management (`otm_b2b_marketing`)

A proprietary module built by Otomater for Logic School Of Management, for
managing B2B Marketing activities with Schools, Colleges, Universities,
Coaching Centres and Training Institutes.

**License:** OPL-1 (proprietary) &middot; **Built by:** Otomater
(https://otomater.com) &middot; **For:** Logic School Of Management

## Features

- **Institution master** — full profile (type, address, GPS, key contacts,
  academic strength, courses offered, status, assigned Marketing Manager /
  Salesperson, tags) with multi-company support.
- **Visit Planning** — future visits with priority, assignment, and a
  draft → planned → completed/cancelled workflow. "Start Visit" auto-creates
  the linked Visit Record.
- **Visit Records** — GPS-tagged check-in/check-out, duration, activity
  type, discussion summary, next follow-up, collected counts (prospects /
  students / parents / faculty contacts), competitor intel, photo /
  business-card / location-photo capture, and attachments.
- **Contacts** — multiple contact persons per institution (Principal, VP,
  HOD, Placement/Admission Officer, etc.).
- **Lead Collection** — leads captured during a visit, with counselor
  assignment and a new → contacted → interested → admission/lost pipeline.
- **Seminar Management** — seminar/event records with attendance, feedback,
  outcome, and interested-student tracking.
- **MOU Management** — discussion → proposal → review → approval → signed →
  renewed/rejected lifecycle, with agreement number, dates, and attachment.
- **Automatic KPIs on the Institution form** — total visits, first/last
  visit date, days since last visit, upcoming visit, leads/seminars/MOUs
  collected — plus smart buttons for Visits, Seminars, Leads, MOU, Contacts.
- **Telegram notifications** — each officer taps "Connect Telegram" on the
  dashboard once; a personal deep link (`t.me/<bot>?start=<token>`) maps
  their chat automatically via a webhook handshake, no chat ID is ever
  entered by hand. Once connected they get visit reminders, follow-up
  alerts, MOU expiry warnings, and the mobile portal link automatically on
  check-in/check-out.
- **OWL Dashboard** — KPI cards (today's/upcoming/completed/pending visits,
  institutions assigned, leads, seminars, MOU signed, etc.), institution
  type and district-wise distributions, and an upcoming-visits list.
  Marketing Executives automatically see only their own institutions and
  visits (scoped server-side); Marketing Manager/Head see everything.
- **Reports** — Institution Visit, Executive Performance, Lead Collection,
  Seminar, MOU, Monthly Visit, and Institution Type / District Wise reports
  as pivot/graph analysis views, plus printable Visit Report and MOU
  Summary PDFs.
- **Security** — three-tier groups (Marketing Executive / Manager / Head)
  with record rules restricting Executives to their own assigned
  institutions and visits, and a Python guard preventing Executives from
  deleting completed visit records.
- **Automated reminders** — daily scheduled actions raise to-do activities
  for today's/tomorrow's planned visits, pending follow-ups, and MOUs
  expiring within 30 days.
- **Bulk tool** — "Assign Marketing Manager" wizard, available from the
  Institutions list view, to reassign multiple institutions at once.
- Full chatter (followers, internal notes, attachments, activities) on
  Institution, Visit Plan, Visit Record, Lead, Seminar, and MOU.

## Technical Notes (Odoo 19)

- Models use the `otm.` prefix (`otm.b2b.institution`, `otm.b2b.visit.plan`,
  etc.) per Otomater convention — this is a proprietary product, not a
  Community Edition addon.
- Views use `<list>` (not `<tree>`) and inline `invisible=`/`readonly=`
  expressions (not `attrs=`).
- Chatter uses the `<chatter/>` shorthand.
- No SCSS — dashboard styling is plain CSS registered on
  `web.assets_backend`.
- The OWL dashboard component declares `static props = ["*"]` and imports
  services via `useService`; session data is not read via
  `useService("session")`.
- `post_init_hook` grants the Marketing Head group to the installing admin
  user so the module is usable immediately after install.
- Run `validate_odoo19_module.py otm_b2b_marketing` and
  `check_forward_refs.py otm_b2b_marketing` before every delivery.

## Module Structure

```
otm_b2b_marketing/
├── __init__.py
├── __manifest__.py
├── hooks.py
├── models/
├── views/
├── wizard/
├── report/
├── data/
├── security/
└── static/
    ├── description/icon.png
    └── src/{js,xml,css}/
```

## Installation

1. Copy `otm_b2b_marketing` into your Odoo 19 custom addons path.
2. Update the apps list and install **Otomater B2B Marketing**.
3. Assign users to **Marketing Executive**, **Marketing Manager**, or
   **Marketing Head** under Settings → Users.
4. Configure Institution Types / Activity Types / Tags under
   B2B Marketing → Configuration (defaults are pre-loaded).
