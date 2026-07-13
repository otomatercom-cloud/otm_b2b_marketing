# -*- coding: utf-8 -*-
from odoo import fields, models


class OtmB2bTag(models.Model):
    """Free-form tags for institutions (e.g. 'Priority', 'Rural', 'Metro')."""
    _name = 'otm.b2b.tag'
    _description = 'B2B Institution Tag'
    _order = 'name'

    name = fields.Char(string='Tag', required=True, translate=True)
    color = fields.Integer(string='Color Index')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'A tag with this name already exists.'),
    ]
