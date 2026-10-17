# -*- coding: utf-8 -*-
from odoo import api, fields, models


class OtmB2bLead(models.Model):
    """A prospective student lead collected during a B2B institutional visit."""
    _name = 'otm.b2b.lead'
    _description = 'B2B Lead'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id desc'

    name = fields.Char(string='Student Name', required=True, tracking=True)
    mobile = fields.Char(string='Mobile')
    email = fields.Char(string='Email')
    course_interested = fields.Char(string='Course Interested')
    current_class = fields.Char(string='Current Class')
    institution_id = fields.Many2one('otm.b2b.institution', string='Institution', index=True, tracking=True)
    visit_id = fields.Many2one('otm.b2b.visit.record', string='Visit', index=True)
    source = fields.Selection([
        ('b2b_visit', 'B2B Visit'),
        ('seminar', 'Seminar'),
        ('referral', 'Referral'),
        ('website', 'Website'),
        ('other', 'Other'),
    ], string='Source', default='b2b_visit', required=True)
    seminar_id = fields.Many2one(
        'otm.b2b.seminar', string='Seminar', index=True, ondelete='set null',
        help='Seminar this student was collected at (Excel upload or online form).')
    entry_mode = fields.Selection([
        ('manual', 'Manual'),
        ('excel', 'Excel Upload (hardcopy)'),
        ('online_form', 'Online Form'),
    ], string='Collected Via', default='manual', required=True)
    stream_id = fields.Many2one('otm.b2b.stream', string='Stream', tracking=True)
    source_campaign = fields.Char(
        string='Source Campaign', tracking=True,
        help='Campaign / event this lead came from. Auto-filled for seminar leads '
             '(e.g. "Seminar - Institution - 17 Oct 2026") when left blank.')
    counselor_id = fields.Many2one('res.users', string='Assigned Counselor', tracking=True)
    state = fields.Selection([
        ('new', 'New'),
        ('contacted', 'Contacted'),
        ('interested', 'Interested'),
        ('admission', 'Admission'),
        ('lost', 'Lost'),
    ], string='Status', default='new', required=True, tracking=True)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('seminar_id') and not vals.get('source_campaign'):
                seminar = self.env['otm.b2b.seminar'].browse(vals['seminar_id'])
                vals['source_campaign'] = 'Seminar - %s - %s' % (
                    seminar.institution_id.name, fields.Date.to_string(seminar.seminar_date))
        return super().create(vals_list)

    def action_set_contacted(self):
        self.write({'state': 'contacted'})

    def action_set_interested(self):
        self.write({'state': 'interested'})

    def action_set_admission(self):
        self.write({'state': 'admission'})

    def action_set_lost(self):
        self.write({'state': 'lost'})
