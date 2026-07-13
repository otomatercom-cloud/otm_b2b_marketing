# -*- coding: utf-8 -*-
from odoo import fields, models


class OtmB2bTier(models.Model):
    """Institution category / tier used for prioritization, e.g. Tier 1, Tier 2."""
    _name = 'otm.b2b.tier'
    _description = 'B2B Institution Category / Tier'
    _order = 'sequence, name'

    name = fields.Char(string='Category / Tier', required=True, translate=True)
    code = fields.Char(string='Code')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'A category/tier with this name already exists.'),
    ]
