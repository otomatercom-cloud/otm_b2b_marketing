# -*- coding: utf-8 -*-
from odoo import fields, models


class OtmB2bZone(models.Model):
    """Marketing zone used to territory-map institutions, e.g. Zone 1, Zone 2."""
    _name = 'otm.b2b.zone'
    _description = 'B2B Marketing Zone'
    _order = 'sequence, name'

    name = fields.Char(string='Zone', required=True, translate=True)
    code = fields.Char(string='Code')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'A zone with this name already exists.'),
    ]
