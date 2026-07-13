# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class OtmB2bVisitPlan(models.Model):
    """Future visit plans created by a Marketing Manager/Executive."""
    _name = 'otm.b2b.visit.plan'
    _description = 'B2B Visit Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'visit_date desc, id desc'

    institution_id = fields.Many2one(
        'otm.b2b.institution', string='Institution', required=True,
        tracking=True, index=True)
    filter_tier_id = fields.Many2one(
        'otm.b2b.tier', string='Filter by Category / Tier',
        help='Pick a Tier here to narrow the Institution list below to that category only.')
    filter_zone_id = fields.Many2one(
        'otm.b2b.zone', string='Filter by Zone',
        help='Pick a Zone here to narrow the Institution list below to that zone only.')
    tier_id = fields.Many2one(related='institution_id.tier_id', string='Category / Tier', store=True, readonly=True)
    zone_id = fields.Many2one(related='institution_id.zone_id', string='Zone', store=True, readonly=True)
    visit_date = fields.Date(string='Visit Date', required=True, tracking=True)
    expected_time = fields.Float(string='Expected Time')
    purpose = fields.Char(string='Purpose')
    priority = fields.Selection([
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], string='Priority', default='medium', required=True)
    user_id = fields.Many2one(
        'res.users', string='Assigned To', required=True, tracking=True,
        default=lambda self: self.env.user)
    state = fields.Selection([
        ('draft', 'Draft'),
        ('planned', 'Planned'),
        ('in_progress', 'Checked In'),
        ('completed', 'Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Status', default='draft', required=True, tracking=True)
    visit_record_id = fields.Many2one('otm.b2b.visit.record', string='Visit Record', readonly=True, copy=False)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)

    def action_confirm_plan(self):
        self.write({'state': 'planned'})

    def action_cancel_plan(self):
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    @api.model
    def _cron_send_visit_reminders(self):
        """Scheduled action: log a reminder activity for today's and
        tomorrow's planned visits, and for visit records with a pending
        followup date, so Marketing Executives get a to-do in their
        Activities list."""
        today = fields.Date.context_today(self)
        tomorrow = fields.Date.add(today, days=1)
        plans = self.search([
            ('state', '=', 'planned'),
            ('visit_date', 'in', [today, tomorrow]),
        ])
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        for plan in plans:
            label = _('Today') if plan.visit_date == today else _('Tomorrow')
            plan.activity_schedule(
                activity_type_id=activity_type.id if activity_type else False,
                summary=_('B2B Visit Reminder (%s)', label),
                note=_('Planned visit to %s on %s.', plan.institution_id.name, plan.visit_date),
                date_deadline=plan.visit_date,
                user_id=plan.user_id.id,
            )

        followups = self.env['otm.b2b.visit.record'].search([
            ('next_followup_date', '=', today),
            ('state', '!=', 'cancelled'),
        ])
        for visit in followups:
            visit.activity_schedule(
                activity_type_id=activity_type.id if activity_type else False,
                summary=_('B2B Follow-up Due'),
                note=_('Follow-up due today for %s.', visit.institution_id.name),
                date_deadline=today,
                user_id=visit.user_id.id,
            )

    def action_open_complete_wizard(self):
        self.ensure_one()
        # If the officer already checked in, a Visit Record exists for
        # this plan - complete THAT record (sets checkout time) rather
        # than creating a second one.
        context = (
            {'default_visit_record_id': self.visit_record_id.id}
            if self.visit_record_id
            else {'default_visit_plan_id': self.id}
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Complete Visit'),
            'res_model': 'otm.b2b.visit.complete.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': context,
        }

    def action_check_in(self):
        """Officer has arrived at the institution: create the Visit
        Record, stamp check-in time, and move the plan to 'Checked In'.
        The visit is completed later via Check Out / the Complete Visit
        wizard, either from here or from the Visit Record itself."""
        self.ensure_one()
        visit = self.env['otm.b2b.visit.record'].create({
            'institution_id': self.institution_id.id,
            'visit_plan_id': self.id,
            'user_id': self.user_id.id,
            'visit_date': fields.Date.context_today(self),
            'company_id': self.company_id.id,
            'checkin_time': fields.Datetime.now(),
        })
        self.write({'state': 'in_progress', 'visit_record_id': visit.id})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'otm.b2b.visit.record',
            'view_mode': 'form',
            'res_id': visit.id,
        }

    def action_dashboard_check_in(self):
        """Same check-in as action_check_in, but returns plain data
        instead of an act_window so the Dashboard widget can show the
        portal link immediately without navigating away."""
        self.ensure_one()
        self.action_check_in()
        return {
            'institution': self.institution_id.name,
            'visit_id': self.visit_record_id.id,
            'portal_url': self.visit_record_id.portal_url,
        }
