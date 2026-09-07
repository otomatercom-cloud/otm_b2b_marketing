# -*- coding: utf-8 -*-
import uuid

from odoo import api, fields, models, _


class OtmB2bSeminar(models.Model):
    """Seminar / campus event conducted at an institution. Created at
    check-in (via otm.b2b.seminar.plan.action_check_in) with just the
    institution and date known; the rest is filled in at Check Out via
    the Complete Seminar wizard or the public portal form, mirroring
    otm.b2b.visit.record's check-in/check-out/portal pattern."""
    _name = 'otm.b2b.seminar'
    _description = 'B2B Seminar'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'seminar_date desc, id desc'

    institution_id = fields.Many2one('otm.b2b.institution', string='Institution', required=True,
                                      tracking=True, index=True)
    visit_id = fields.Many2one('otm.b2b.visit.record', string='Visit')
    seminar_plan_id = fields.Many2one('otm.b2b.seminar.plan', string='Seminar Plan', readonly=True, copy=False)
    seminar_date = fields.Date(string='Seminar Date', required=True, tracking=True)
    topic = fields.Char(string='Topic')
    category_ids = fields.Many2many(
        'otm.b2b.seminar.category', string='Categories',
        help='Class/course categories this seminar covered, e.g. Plus 1 Commerce, B.Com 1st Year. '
             'Select as many as apply.')
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

    checkin_time = fields.Datetime(string='Check In Time')
    checkout_time = fields.Datetime(string='Check Out Time')
    gps_latitude = fields.Float(string='GPS Latitude', digits=(16, 6))
    gps_longitude = fields.Float(string='GPS Longitude', digits=(16, 6))
    map_url = fields.Char(string='Map Link', compute='_compute_map_url')
    state = fields.Selection([
        ('draft', 'Draft'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)

    access_token = fields.Char(string='Access Token', copy=False, readonly=True,
                                default=lambda self: uuid.uuid4().hex)
    portal_url = fields.Char(string='Portal Link', compute='_compute_portal_url')

    def _compute_portal_url(self):
        base_url = self.env['ir.config_parameter'].sudo().get_param('web.base.url')
        for rec in self:
            is_saved = isinstance(rec.id, int)
            rec.portal_url = (
                f"{base_url}/b2b/seminar/{rec.id}/{rec.access_token}"
                if is_saved and rec.access_token else False
            )

    def write(self, vals):
        # Fire the completion confirmation exactly once, no matter which
        # completion path triggered it (backend, wizard, or portal form) -
        # same single-choke-point pattern as otm.b2b.visit.record.write().
        newly_completed = self.browse()
        if vals.get('state') == 'completed':
            newly_completed = self.filtered(lambda s: s.state != 'completed')
        result = super().write(vals)
        for seminar in newly_completed:
            plan = seminar.seminar_plan_id
            if plan and plan.user_id.otm_telegram_connected:
                plan.user_id._otm_telegram_send(
                    f"Seminar at {seminar.institution_id.name} recorded successfully. Thank you!"
                )
        return result

    def _compute_map_url(self):
        for rec in self:
            rec.map_url = (
                f"https://www.google.com/maps?q={rec.gps_latitude},{rec.gps_longitude}"
                if rec.gps_latitude or rec.gps_longitude else False
            )

    def action_check_out(self, latitude=None, longitude=None):
        self.write({'checkout_time': fields.Datetime.now()})
        for seminar in self:
            if (not seminar.gps_latitude and not seminar.gps_longitude
                    and latitude is not None and longitude is not None):
                seminar.write({'gps_latitude': latitude, 'gps_longitude': longitude})

    def action_open_complete_wizard(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Complete Seminar'),
            'res_model': 'otm.b2b.seminar.complete.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {'default_seminar_id': self.id},
        }
