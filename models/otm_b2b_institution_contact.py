# -*- coding: utf-8 -*-
from odoo import fields, models


class OtmB2bInstitutionContact(models.Model):
    """Contact persons attached to an institution (Principal, HOD, etc.)."""
    _name = 'otm.b2b.institution.contact'
    _description = 'B2B Institution Contact Person'
    _order = 'institution_id, sequence, name'

    institution_id = fields.Many2one(
        'otm.b2b.institution', string='Institution',
        required=True, ondelete='cascade', index=True)
    sequence = fields.Integer(string='Sequence', default=10)
    name = fields.Char(string='Name', required=True)
    designation = fields.Selection([
        ('principal', 'Principal'),
        ('vice_principal', 'Vice Principal'),
        ('director', 'Director'),
        ('administrator', 'Administrator'),
        ('placement_officer', 'Placement Officer'),
        ('admission_officer', 'Admission Officer'),
        ('faculty', 'Faculty'),
        ('hod', 'HOD'),
        ('office_staff', 'Office Staff'),
        ('other', 'Other'),
    ], string='Designation', default='other', required=True)
    mobile = fields.Char(string='Mobile')
    email = fields.Char(string='Email')
    whatsapp = fields.Char(string='WhatsApp Number')
    birthday = fields.Date(string='Birthday')
    remarks = fields.Text(string='Remarks')
    company_id = fields.Many2one(related='institution_id.company_id', store=True, readonly=True)
