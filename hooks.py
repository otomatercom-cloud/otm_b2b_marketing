# -*- coding: utf-8 -*-
import uuid

_TOKEN_FIELDS = (
    ('res.users', 'otm_telegram_link_token'),
    ('otm.b2b.visit.record', 'access_token'),
    ('otm.b2b.seminar', 'access_token'),
)


def dedupe_tokens(env):
    """A new column with a callable default is filled with ONE value for all
    pre-existing rows, so rows that existed before this module added the
    column can share an identical token. Give every duplicate/empty token a
    fresh unique value (idempotent - safe to run repeatedly)."""
    for model, field in _TOKEN_FIELDS:
        records = env[model].sudo().with_context(active_test=False).search([])
        seen = set()
        for rec in records:
            token = rec[field]
            if not token or token in seen:
                rec.write({field: uuid.uuid4().hex})
            seen.add(rec[field])



def post_init_hook(env):
    """Post-install seeding that must run after every dependency (base, mail)
    is fully loaded — per Rule 17, avoid relying on plain data/*.xml load
    order for ACL/group membership seeding.

    Grants the installing admin user the Marketing Head group so the module
    is immediately usable after install, without requiring a manual
    Settings > Users step first.
    """
    dedupe_tokens(env)
    admin_group = env.ref('otm_b2b_marketing.group_otm_b2b_marketing_head', raise_if_not_found=False)
    if not admin_group:
        return
    superuser = env.ref('base.user_admin', raise_if_not_found=False)
    if superuser:
        # Odoo 19 renamed res.users.groups_id -> group_ids as part of the
        # res.groups.privilege restructuring (see ODOO19_RULES.md Rule 6).
        superuser.write({'group_ids': [(4, admin_group.id)]})
