# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class OtmB2bSeminarBookWizard(models.TransientModel):
    """Small popup shown when "Book Seminar" is clicked on an
    Institution: just pick the date and confirm. Unlike the instant
    "Plan Visit" button (which silently defaults to today), seminars are
    more often booked ahead of time, so this asks for the date rather
    than assuming today."""
    _name = 'otm.b2b.seminar.book.wizard'
    _description = 'Book Seminar'

    institution_id = fields.Many2one('otm.b2b.institution', string='Institution', required=True, readonly=True)
    seminar_date = fields.Date(string='Seminar Date', required=True, default=fields.Date.context_today)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id and self.env.context.get('active_model') == 'otm.b2b.institution':
            res['institution_id'] = active_id
        return res

    def action_confirm(self):
        self.ensure_one()
        existing = self.env['otm.b2b.seminar.plan'].search([
            ('institution_id', '=', self.institution_id.id),
            ('user_id', '=', self.env.uid),
            ('seminar_date', '=', self.seminar_date),
            ('state', 'in', ('draft', 'planned', 'in_progress')),
        ], limit=1)
        if existing:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Already Booked'),
                    'message': _('A seminar is already booked at %s on %s.',
                                  self.institution_id.name, self.seminar_date),
                    'type': 'warning',
                    # display_notification alone only shows a toast - it
                    # does NOT close this popup on its own. Chaining a
                    # 'next' act_window_close is the standard way to do
                    # both: show the message, then close the dialog.
                    'next': {'type': 'ir.actions.act_window_close'},
                },
            }

        self.env['otm.b2b.seminar.plan'].create({
            'institution_id': self.institution_id.id,
            'seminar_date': self.seminar_date,
            'user_id': self.env.uid,
            'company_id': self.institution_id.company_id.id,
            'state': 'planned',
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Booked'),
                'message': _('Seminar booked at %s for %s.', self.institution_id.name, self.seminar_date),
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
