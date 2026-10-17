# -*- coding: utf-8 -*-
from odoo import fields, models


class OtmB2bStream(models.Model):
    """Student's academic stream (Commerce, Science, Humanities...) used
    on seminar leads. Admin-extendable master."""
    _name = 'otm.b2b.stream'
    _description = 'B2B Student Stream'
    _order = 'sequence, name'

    name = fields.Char(string='Stream', required=True, translate=True)
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'A stream with this name already exists.'),
    ]
