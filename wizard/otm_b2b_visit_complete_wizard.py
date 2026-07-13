# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class OtmB2bVisitCompleteWizard(models.TransientModel):
    """Quick post-visit update: Marketing Executive fills only Activity
    Type + Remarks (plus optional follow-up) and marks the visit done, in
    one step, without opening the full Visit Record form."""
    _name = 'otm.b2b.visit.complete.wizard'
    _description = 'Complete Visit'

    visit_plan_id = fields.Many2one('otm.b2b.visit.plan', string='Visit Plan')
    visit_record_id = fields.Many2one('otm.b2b.visit.record', string='Visit Record')
    institution_id = fields.Many2one('otm.b2b.institution', string='Institution', readonly=True)
    marketing_activity_type_id = fields.Many2one(
        'otm.b2b.activity.type', string='Activity Type', required=True)
    remarks = fields.Text(string='Remarks', required=True)
    next_action = fields.Char(string='Next Action')
    next_followup_date = fields.Date(string='Next Followup Date')
    portal_url = fields.Char(string='Portal Link', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        context = self.env.context
        visit_plan_id = context.get('default_visit_plan_id')
        visit_record_id = context.get('default_visit_record_id')
        if visit_plan_id:
            plan = self.env['otm.b2b.visit.plan'].browse(visit_plan_id)
            res['institution_id'] = plan.institution_id.id
        elif visit_record_id:
            visit = self.env['otm.b2b.visit.record'].browse(visit_record_id)
            res['institution_id'] = visit.institution_id.id
            res['portal_url'] = visit.portal_url
        return res

    def action_complete(self):
        self.ensure_one()
        now = fields.Datetime.now()

        if self.visit_record_id:
            visit = self.visit_record_id
            vals = {
                'marketing_activity_type_id': self.marketing_activity_type_id.id,
                'remarks': self.remarks,
                'next_action': self.next_action,
                'next_followup_date': self.next_followup_date,
                'state': 'completed',
                'checkout_time': visit.checkout_time or now,
            }
            if not visit.checkin_time:
                vals['checkin_time'] = now
            visit.write(vals)
            if visit.visit_plan_id and visit.visit_plan_id.state != 'completed':
                visit.visit_plan_id.write({'state': 'completed'})
        elif self.visit_plan_id:
            plan = self.visit_plan_id
            visit = self.env['otm.b2b.visit.record'].create({
                'institution_id': plan.institution_id.id,
                'visit_plan_id': plan.id,
                'user_id': plan.user_id.id,
                'visit_date': fields.Date.context_today(self),
                'company_id': plan.company_id.id,
                'marketing_activity_type_id': self.marketing_activity_type_id.id,
                'remarks': self.remarks,
                'next_action': self.next_action,
                'next_followup_date': self.next_followup_date,
                'state': 'completed',
                'checkin_time': now,
                'checkout_time': now,
            })
            plan.write({'state': 'completed', 'visit_record_id': visit.id})
        else:
            raise ValueError(_('No visit plan or visit record was provided to complete.'))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'otm.b2b.visit.record',
            'view_mode': 'form',
            'res_id': visit.id,
        }
