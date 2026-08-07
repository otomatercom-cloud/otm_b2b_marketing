# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class OtmB2bVisitPlanBookWizard(models.TransientModel):
    """Small popup shown when "Plan Visit for Future" is clicked on an
    Institution: just pick the date and confirm. Mirrors
    otm.b2b.seminar.book.wizard - unlike "Plan Visit for Today" (which
    silently defaults to today, no popup), this is for scheduling ahead."""
    _name = 'otm.b2b.visit.plan.book.wizard'
    _description = 'Plan Visit for Future'

    institution_id = fields.Many2one('otm.b2b.institution', string='Institution', required=True, readonly=True)
    visit_date = fields.Date(string='Visit Date', required=True, default=fields.Date.context_today)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get('active_id')
        if active_id and self.env.context.get('active_model') == 'otm.b2b.institution':
            res['institution_id'] = active_id
        return res

    def action_confirm(self):
        self.ensure_one()
        existing = self.env['otm.b2b.visit.plan'].search([
            ('institution_id', '=', self.institution_id.id),
            ('user_id', '=', self.env.uid),
            ('visit_date', '=', self.visit_date),
            ('state', 'in', ('draft', 'planned', 'in_progress')),
        ], limit=1)
        if existing:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('Already Planned'),
                    'message': _('A visit is already planned at %s on %s.',
                                  self.institution_id.name, self.visit_date),
                    'type': 'warning',
                    'next': {'type': 'ir.actions.act_window_close'},
                },
            }

        self.env['otm.b2b.visit.plan'].create({
            'institution_id': self.institution_id.id,
            'visit_date': self.visit_date,
            'user_id': self.env.uid,
            'company_id': self.institution_id.company_id.id,
            'state': 'planned',
        })
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Planned'),
                'message': _('Visit planned at %s for %s.', self.institution_id.name, self.visit_date),
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
