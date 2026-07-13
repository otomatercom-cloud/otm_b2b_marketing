# -*- coding: utf-8 -*-
from odoo import fields, models


class OtmB2bSeminar(models.Model):
    """Seminar / campus event conducted at an institution."""
    _name = 'otm.b2b.seminar'
    _description = 'B2B Seminar'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'seminar_date desc, id desc'

    institution_id = fields.Many2one('otm.b2b.institution', string='Institution', required=True,
                                      tracking=True, index=True)
    visit_id = fields.Many2one('otm.b2b.visit.record', string='Visit')
    seminar_date = fields.Date(string='Seminar Date', required=True, tracking=True)
    topic = fields.Char(string='Topic', required=True)
    speaker = fields.Char(string='Speaker')
    student_count = fields.Integer(string='Number of Students')
    faculty_count = fields.Integer(string='Number of Faculty')
    duration = fields.Float(string='Duration (Hours)')
    feedback = fields.Text(string='Feedback')
    outcome = fields.Text(string='Outcome')
    interested_students = fields.Integer(string='Interested Students')
    photo = fields.Image(string='Photo', max_width=1920, max_height=1920)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)
