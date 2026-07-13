# -*- coding: utf-8 -*-
from odoo import fields, models


class OtmB2bUniversity(models.Model):
    """Affiliating university, e.g. MGU, Calicut University."""
    _name = 'otm.b2b.university'
    _description = 'B2B Affiliated University'
    _order = 'sequence, name'

    name = fields.Char(string='University', required=True, translate=True)
    code = fields.Char(string='Code')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'A university with this name already exists.'),
    ]
