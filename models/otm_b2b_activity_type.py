# -*- coding: utf-8 -*-
from odoo import fields, models


class OtmB2bActivityType(models.Model):
    """Configurable marketing activity types, e.g. First Visit, MOU Signed."""
    _name = 'otm.b2b.activity.type'
    _description = 'B2B Marketing Activity Type'
    _order = 'sequence, name'

    name = fields.Char(string='Activity Type', required=True, translate=True)
    code = fields.Char(string='Code')
    sequence = fields.Integer(string='Sequence', default=10)
    color = fields.Integer(string='Color Index')
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'An activity type with this name already exists.'),
    ]
