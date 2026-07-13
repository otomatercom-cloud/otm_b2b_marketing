# -*- coding: utf-8 -*-
import uuid

from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class OtmB2bVisitRecord(models.Model):
    """One record per actual field visit made by a Marketing Executive."""
    _name = 'otm.b2b.visit.record'
    _description = 'B2B Visit Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'visit_date desc, id desc'

    name = fields.Char(string='Visit Number', copy=False, readonly=True,
                        default=lambda self: _('New'))
    institution_id = fields.Many2one(
        'otm.b2b.institution', string='Institution', required=True,
        tracking=True, index=True)
    visit_plan_id = fields.Many2one('otm.b2b.visit.plan', string='Visit Plan', readonly=True, copy=False)
    user_id = fields.Many2one(
        'res.users', string='Marketing Executive', required=True, tracking=True,
        default=lambda self: self.env.user)
    visit_date = fields.Date(string='Visit Date', required=True, tracking=True,
                              default=fields.Date.context_today)

    checkin_time = fields.Datetime(string='Check In Time')
    checkout_time = fields.Datetime(string='Check Out Time')
    duration = fields.Float(string='Duration (Hours)', compute='_compute_duration', store=True)

    gps_latitude = fields.Float(string='GPS Latitude', digits=(16, 6))
    gps_longitude = fields.Float(string='GPS Longitude', digits=(16, 6))

    state = fields.Selection([
        ('draft', 'Draft'),
        ('completed', 'Completed'),
        ('partially_completed', 'Partially Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Visit Status', default='draft', required=True, tracking=True)

    marketing_activity_type_id = fields.Many2one(
        'otm.b2b.activity.type', string='Activity Type', tracking=True)
    remarks = fields.Text(string='Remarks')
    discussion_summary = fields.Text(string='Discussion Summary')
    next_followup_date = fields.Date(string='Next Followup Date', tracking=True)
    next_action = fields.Char(string='Next Action')

    collected_prospect_count = fields.Integer(string='Collected Prospect Count')
    collected_student_count = fields.Integer(string='Collected Student Count')
    collected_parent_count = fields.Integer(string='Collected Parent Count')
    collected_faculty_contact_count = fields.Integer(string='Collected Faculty Contact Count')
    interested_courses = fields.Text(string='Interested Courses')
    competitor_name = fields.Char(string='Competitor Name')
    competitor_fees = fields.Monetary(string='Competitor Fees', currency_field='currency_id')
    currency_id = fields.Many2one('res.currency', default=lambda self: self.env.company.currency_id)

    photo = fields.Image(string='Photo', max_width=1920, max_height=1920)
    business_card = fields.Image(string='Business Card', max_width=1920, max_height=1920)
    location_photo = fields.Image(string='Location Photo', max_width=1920, max_height=1920)
    attachment_ids = fields.Many2many('ir.attachment', string='Attachments')

    lead_ids = fields.One2many('otm.b2b.lead', 'visit_id', string='Leads Collected')
    lead_count = fields.Integer(string='Lead Count', compute='_compute_lead_count')

    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)

    # Public, token-protected link so a Marketing Executive can complete a
    # visit from their phone without a backend login (backup to the
    # in-app wizard). No 'portal'/'website' module dependency needed -
    # this is a plain public controller guarded by the token below.
    access_token = fields.Char(string='Access Token', copy=False, readonly=True,
                                default=lambda self: uuid.uuid4().hex)
    portal_url = fields.Char(string='Portal Link', compute='_compute_portal_url')

    _sql_constraints = [
        ('name_uniq', 'unique(name, company_id)', 'Visit Number must be unique per company.'),
    ]

    @api.depends('checkin_time', 'checkout_time')
    def _compute_duration(self):
        for rec in self:
            if rec.checkin_time and rec.checkout_time and rec.checkout_time > rec.checkin_time:
                delta = rec.checkout_time - rec.checkin_time
                rec.duration = round(delta.total_seconds() / 3600.0, 2)
            else:
                rec.duration = 0.0

    def _compute_lead_count(self):
        for rec in self:
            rec.lead_count = len(rec.lead_ids)

    def _compute_portal_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            # A real saved record always has an int id; an unsaved/onchange
            # record has a NewId placeholder instead. Checking
            # isinstance(..., int) avoids depending on NewId's exact import
            # path (it moved from odoo.models to odoo.orm.identifiers
            # between versions) - this check is stable across versions.
            is_saved = isinstance(rec.id, int)
            rec.portal_url = (
                f"{base_url}/b2b/visit/{rec.id}/{rec.access_token}"
                if is_saved and rec.access_token else False
            )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code('otm.b2b.visit.record') or _('New')
        return super().create(vals_list)

    def action_check_in(self):
        self.write({'checkin_time': fields.Datetime.now()})

    def action_check_out(self):
        self.write({'checkout_time': fields.Datetime.now()})

    def action_mark_completed(self):
        self.write({'state': 'completed'})

    def action_mark_partial(self):
        self.write({'state': 'partially_completed'})

    def action_cancel(self):
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_open_complete_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Complete Visit'),
            'res_model': 'otm.b2b.visit.complete.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_visit_record_id': self.id},
        }

    def action_view_leads(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Leads Collected'),
            'res_model': 'otm.b2b.lead',
            'view_mode': 'list,form',
            'domain': [('visit_id', '=', self.id)],
            'context': {'default_visit_id': self.id, 'default_institution_id': self.institution_id.id},
        }

    def unlink(self):
        for rec in self:
            if rec.state == 'completed' and not self.env.user.has_group(
                    'otm_b2b_marketing.group_otm_b2b_marketing_manager'):
                raise ValidationError(_(
                    'Completed visit records cannot be deleted by a Marketing Executive. '
                    'Ask a Marketing Manager or Head.'))
        return super().unlink()
