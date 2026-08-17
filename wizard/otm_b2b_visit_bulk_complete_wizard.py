# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class OtmB2bVisitBulkCompleteWizard(models.TransientModel):
    """Bulk-complete a selection of Visit Records from the list view -
    for clearing a backlog of old Draft visits at once, rather than
    opening and completing each one individually. Applies the same
    Activity Type and Remarks to every selected visit; leave Remarks
    blank to only stamp them completed without overwriting anything
    already on the record."""
    _name = 'otm.b2b.visit.bulk.complete.wizard'
    _description = 'Bulk Complete Visits'

    visit_ids = fields.Many2many('otm.b2b.visit.record', string='Visits', required=True)
    marketing_activity_type_id = fields.Many2one(
        'otm.b2b.activity.type', string='Activity Type', required=True,
        help='Applied to every selected visit.')
    remarks = fields.Text(
        string='Remarks',
        help='Applied to every selected visit. Leave blank to keep each visit\'s '
             'existing remarks (if any) untouched.')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('active_model') == 'otm.b2b.visit.record':
            active_ids = self.env.context.get('active_ids', [])
            visits = self.env['otm.b2b.visit.record'].browse(active_ids)
            already_done = visits.filtered(lambda v: v.state == 'completed')
            res['visit_ids'] = [(6, 0, (visits - already_done).ids)]
        return res

    def action_complete(self):
        self.ensure_one()
        if not self.visit_ids:
            raise UserError(_('No visits to complete - they may already be marked done.'))

        now = fields.Datetime.now()
        for visit in self.visit_ids:
            vals = {
                'marketing_activity_type_id': self.marketing_activity_type_id.id,
                'state': 'completed',
                'checkout_time': visit.checkout_time or now,
            }
            if not visit.checkin_time:
                vals['checkin_time'] = now
            if self.remarks:
                vals['remarks'] = self.remarks
            visit.write(vals)
            if visit.visit_plan_id and visit.visit_plan_id.state != 'completed':
                visit.visit_plan_id.write({'state': 'completed'})

        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Done'),
                'message': _('%s visit(s) marked completed.', len(self.visit_ids)),
                'type': 'success',
                'next': {'type': 'ir.actions.act_window_close'},
            },
        }
