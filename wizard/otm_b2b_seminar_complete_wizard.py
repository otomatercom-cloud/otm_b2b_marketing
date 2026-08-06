# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class OtmB2bSeminarCompleteWizard(models.TransientModel):
    """Quick post-seminar update: fill in the categories covered,
    feedback, and attendance, and mark the seminar done in one step,
    without opening the full Seminar form. Mirrors
    otm.b2b.visit.complete.wizard's shape."""
    _name = 'otm.b2b.seminar.complete.wizard'
    _description = 'Complete Seminar'

    seminar_plan_id = fields.Many2one('otm.b2b.seminar.plan', string='Seminar Plan')
    seminar_id = fields.Many2one('otm.b2b.seminar', string='Seminar Record')
    institution_id = fields.Many2one('otm.b2b.institution', string='Institution', readonly=True)
    topic = fields.Char(string='Topic')
    category_ids = fields.Many2many(
        'otm.b2b.seminar.category', string='Categories', required=True,
        help='Class/course categories covered - select as many as apply.')
    speaker = fields.Char(string='Speaker')
    student_count = fields.Integer(string='Number of Students')
    faculty_count = fields.Integer(string='Number of Faculty')
    interested_students = fields.Integer(string='Interested Students')
    feedback = fields.Text(string='Feedback')
    outcome = fields.Text(string='Outcome')
    portal_url = fields.Char(string='Portal Link', readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        context = self.env.context
        seminar_plan_id = context.get('default_seminar_plan_id')
        seminar_id = context.get('default_seminar_id')
        if seminar_plan_id:
            plan = self.env['otm.b2b.seminar.plan'].browse(seminar_plan_id)
            res['institution_id'] = plan.institution_id.id
        elif seminar_id:
            seminar = self.env['otm.b2b.seminar'].browse(seminar_id)
            res['institution_id'] = seminar.institution_id.id
            res['portal_url'] = seminar.portal_url
        return res

    def action_complete(self):
        self.ensure_one()
        now = fields.Datetime.now()
        vals = {
            'topic': self.topic,
            'category_ids': [(6, 0, self.category_ids.ids)],
            'speaker': self.speaker,
            'student_count': self.student_count,
            'faculty_count': self.faculty_count,
            'interested_students': self.interested_students,
            'feedback': self.feedback,
            'outcome': self.outcome,
            'state': 'completed',
        }

        if self.seminar_id:
            seminar = self.seminar_id
            vals['checkout_time'] = seminar.checkout_time or now
            if not seminar.checkin_time:
                vals['checkin_time'] = now
            seminar.write(vals)
            if seminar.seminar_plan_id and seminar.seminar_plan_id.state != 'completed':
                seminar.seminar_plan_id.write({'state': 'completed'})
        elif self.seminar_plan_id:
            plan = self.seminar_plan_id
            vals.update({
                'institution_id': plan.institution_id.id,
                'seminar_plan_id': plan.id,
                'seminar_date': plan.seminar_date,
                'company_id': plan.company_id.id,
                'checkin_time': now,
                'checkout_time': now,
            })
            seminar = self.env['otm.b2b.seminar'].create(vals)
            plan.write({'state': 'completed', 'seminar_id': seminar.id})
        else:
            raise ValueError(_('No seminar plan or seminar record was provided to complete.'))

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'otm.b2b.seminar',
            'view_mode': 'form',
            'res_id': seminar.id,
        }
