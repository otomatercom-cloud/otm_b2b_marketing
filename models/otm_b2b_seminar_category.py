# -*- coding: utf-8 -*-
from odoo import fields, models


class OtmB2bSeminarCategory(models.Model):
    """Class/course category a seminar was conducted for, e.g. 'Plus 1
    Commerce', 'B.Com 1st Year'. Manually created and extended by the
    admin - a seminar can cover several of these at once (multi-select)."""
    _name = 'otm.b2b.seminar.category'
    _description = 'B2B Seminar Category'
    _order = 'sequence, name'

    name = fields.Char(string='Category', required=True, translate=True)
    code = fields.Char(string='Code')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'A category with this name already exists.'),
    ]
