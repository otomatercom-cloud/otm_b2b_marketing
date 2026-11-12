# -*- coding: utf-8 -*-
from odoo import SUPERUSER_ID, api

from odoo.addons.otm_b2b_marketing.hooks import dedupe_tokens


def migrate(cr, version):
    """Security fix SEC-09: make sure no two users / visits / seminars share
    a link or portal token."""
    env = api.Environment(cr, SUPERUSER_ID, {})
    dedupe_tokens(env)
