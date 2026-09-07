# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class OtmB2bSeminarPlan(models.Model):
    """A booked seminar - "Book Seminar" on an Institution creates one of
    these with a chosen date. Mirrors otm.b2b.visit.plan's lifecycle:
    Draft -> Planned -> Checked In -> Completed, with the actual seminar
    record (feedback, categories, attendance) created at check-in and
    filled in at Check Out via the Complete Seminar form."""
    _name = 'otm.b2b.seminar.plan'
    _description = 'B2B Seminar Plan'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'seminar_date desc, id desc'

    institution_id = fields.Many2one(
        'otm.b2b.institution', string='Institution', required=True,
        tracking=True, index=True)
    seminar_date = fields.Date(string='Seminar Date', required=True, tracking=True,
                                default=fields.Date.context_today)
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
    seminar_id = fields.Many2one('otm.b2b.seminar', string='Seminar Record', readonly=True, copy=False)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)

    def action_confirm_plan(self):
        self.write({'state': 'planned'})

    def action_cancel_plan(self):
        self.write({'state': 'cancelled'})

    def action_reset_draft(self):
        self.write({'state': 'draft'})

    def action_open_complete_wizard(self):
        self.ensure_one()
        # If already checked in, a Seminar record exists for this plan -
        # complete THAT record rather than creating a second one.
        context = (
            {'default_seminar_id': self.seminar_id.id}
            if self.seminar_id
            else {'default_seminar_plan_id': self.id}
        )
        return {
            'type': 'ir.actions.act_window',
            'name': _('Complete Seminar'),
            'res_model': 'otm.b2b.seminar.complete.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': context,
        }

    def action_check_in(self, latitude=None, longitude=None):
        """Seminar is starting: create the Seminar record, stamp
        check-in time, move the plan to 'Checked In'. Completed later
        via Check Out / the Complete Seminar wizard."""
        self.ensure_one()
        vals = {
            'institution_id': self.institution_id.id,
            'seminar_plan_id': self.id,
            'seminar_date': self.seminar_date,
            'company_id': self.company_id.id,
            'checkin_time': fields.Datetime.now(),
        }
        if latitude is not None and longitude is not None:
            vals['gps_latitude'] = latitude
            vals['gps_longitude'] = longitude
        seminar = self.env['otm.b2b.seminar'].create(vals)
        self.write({'state': 'in_progress', 'seminar_id': seminar.id})
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'otm.b2b.seminar',
            'view_mode': 'form',
            'res_id': seminar.id,
        }

    def action_dashboard_check_in(self, latitude=None, longitude=None):
        """Same check-in as action_check_in, but returns plain data
        instead of an act_window so the Dashboard widget can show the
        portal link immediately without navigating away."""
        self.ensure_one()
        self.action_check_in(latitude=latitude, longitude=longitude)
        seminar = self.seminar_id
        if self.user_id.otm_telegram_connected:
            self.user_id._otm_telegram_send(
                f"Checked in for seminar at {self.institution_id.name}.\n"
                f"Fill in the seminar details here when you're done: {seminar.portal_url}"
            )
        return {
            'institution': self.institution_id.name,
            'seminar_id': seminar.id,
            'portal_url': seminar.portal_url,
        }

    @api.model
    def _cron_send_seminar_reminders(self):
        """Scheduled action: reminder activity + Telegram nudge for
        seminars booked for today or tomorrow, mirroring the visit
        reminder cron."""
        today = fields.Date.context_today(self)
        tomorrow = fields.Date.add(today, days=1)
        plans = self.search([
            ('state', '=', 'planned'),
            ('seminar_date', 'in', [today, tomorrow]),
        ])
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        for plan in plans:
            label = _('Today') if plan.seminar_date == today else _('Tomorrow')
            plan.activity_schedule(
                activity_type_id=activity_type.id if activity_type else False,
                summary=_('B2B Seminar Reminder (%s)', label),
                note=_('Seminar booked at %s on %s.', plan.institution_id.name, plan.seminar_date),
                date_deadline=plan.seminar_date,
                user_id=plan.user_id.id,
            )
            if plan.user_id.otm_telegram_connected:
                plan.user_id._otm_telegram_send(
                    f"Reminder: seminar at {plan.institution_id.name} planned for "
                    f"{label.lower()} ({plan.seminar_date})."
                )
