# -*- coding: utf-8 -*-
from odoo import fields, models


class OtmB2bInstitutionType(models.Model):
    """Configurable institution categories, e.g. School, College, University."""
    _name = 'otm.b2b.institution.type'
    _description = 'B2B Institution Type'
    _order = 'sequence, name'

    name = fields.Char(string='Institution Type', required=True, translate=True)
    code = fields.Char(string='Code')
    sequence = fields.Integer(string='Sequence', default=10)
    active = fields.Boolean(string='Active', default=True)
    institution_count = fields.Integer(string='Institutions', compute='_compute_institution_count')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'An institution type with this name already exists.'),
    ]

    def _compute_institution_count(self):
        grouped = self.env['otm.b2b.institution']._read_group(
            [('institution_type_id', 'in', self.ids)],
            groupby=['institution_type_id'],
            aggregates=['__count'],
        )
        counts = {inst_type.id: count for inst_type, count in grouped}
        for rec in self:
            rec.institution_count = counts.get(rec.id, 0)
