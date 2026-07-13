# -*- coding: utf-8 -*-


def post_init_hook(env):
    """Post-install seeding that must run after every dependency (base, mail)
    is fully loaded — per Rule 17, avoid relying on plain data/*.xml load
    order for ACL/group membership seeding.

    Grants the installing admin user the Marketing Head group so the module
    is immediately usable after install, without requiring a manual
    Settings > Users step first.
    """
    admin_group = env.ref('otm_b2b_marketing.group_otm_b2b_marketing_head', raise_if_not_found=False)
    if not admin_group:
        return
    superuser = env.ref('base.user_admin', raise_if_not_found=False)
    if superuser:
        # Odoo 19 renamed res.users.groups_id -> group_ids as part of the
        # res.groups.privilege restructuring (see ODOO19_RULES.md Rule 6).
        superuser.write({'group_ids': [(4, admin_group.id)]})
