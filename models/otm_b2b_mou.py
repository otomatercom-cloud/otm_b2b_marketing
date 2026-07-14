# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class OtmB2bMou(models.Model):
    """MOU (Memorandum of Understanding) lifecycle tracking with an institution."""
    _name = 'otm.b2b.mou'
    _description = 'B2B MOU'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'discussion_date desc, id desc'

    institution_id = fields.Many2one('otm.b2b.institution', string='Institution', required=True,
                                      tracking=True, index=True)
    mou_type_id = fields.Many2one('otm.b2b.mou.type', string='MOU Type', tracking=True)
    discussion_date = fields.Date(string='Discussion Date', required=True, tracking=True)
    state = fields.Selection([
        ('discussion', 'Discussion'),
        ('proposal_sent', 'Proposal Sent'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('signed', 'Signed'),
        ('rejected', 'Rejected'),
        ('renewed', 'Renewed'),
    ], string='Status', default='discussion', required=True, tracking=True)
    discussion = fields.Text(string='Discussion Notes')
    agreement_number = fields.Char(string='Agreement Number', copy=False, tracking=True)
    signed_date = fields.Date(string='Signed Date', tracking=True)
    expiry_date = fields.Date(string='Expiry Date', tracking=True)
    renewal_date = fields.Date(string='Renewal Date', tracking=True)
    attachment = fields.Binary(string='Agreement Attachment')
    attachment_filename = fields.Char(string='Attachment Filename')
    remarks = fields.Text(string='Remarks')
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)

    def action_send_proposal(self):
        self.write({'state': 'proposal_sent'})

    def action_under_review(self):
        self.write({'state': 'under_review'})

    def action_approve(self):
        self.write({'state': 'approved'})

    def action_sign(self):
        self.write({'state': 'signed', 'signed_date': fields.Date.context_today(self)})

    def action_reject(self):
        self.write({'state': 'rejected'})

    def action_renew(self):
        self.write({'state': 'renewed'})

    @api.model
    def _cron_mou_expiry_reminders(self):
        """Scheduled action: raise a to-do activity for MOUs expiring within
        the next 30 days so renewal discussions can start in time."""
        today = fields.Date.context_today(self)
        horizon = fields.Date.add(today, days=30)
        expiring = self.search([
            ('state', '=', 'signed'),
            ('expiry_date', '>=', today),
            ('expiry_date', '<=', horizon),
        ])
        activity_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        for mou in expiring:
            mou.activity_schedule(
                activity_type_id=activity_type.id if activity_type else False,
                summary=_('MOU Expiry Reminder'),
                note=_('MOU with %s expires on %s.', mou.institution_id.name, mou.expiry_date),
                date_deadline=mou.expiry_date,
                user_id=mou.institution_id.marketing_manager_id.id or self.env.uid,
            )
            manager = mou.institution_id.marketing_manager_id
            if manager.otm_telegram_connected:
                manager._otm_telegram_send(
                    f"MOU with {mou.institution_id.name} expires on {mou.expiry_date}. "
                    f"Time to start the renewal discussion."
                )
