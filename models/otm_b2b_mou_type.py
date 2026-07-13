# -*- coding: utf-8 -*-
from odoo import fields, models


class OtmB2bMouType(models.Model):
    """Type of MOU, e.g. Placement, Training, Academic."""
    _name = 'otm.b2b.mou.type'
    _description = 'B2B MOU Type'
    _order = 'sequence, name'

    name = fields.Char(string='MOU Type', required=True, translate=True)
    code = fields.Char(string='Code')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'A MOU type with this name already exists.'),
    ]
