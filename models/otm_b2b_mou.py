# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import AccessError, UserError, ValidationError

MANAGER_GROUP = 'otm_b2b_marketing.group_otm_b2b_marketing_manager'


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

    @api.constrains('agreement_number', 'company_id')
    def _check_agreement_unique(self):
        for mou in self.filtered('agreement_number'):
            if self.search_count([('id', '!=', mou.id), ('company_id', '=', mou.company_id.id),
                                  ('agreement_number', '=', mou.agreement_number)]):
                raise ValidationError(_('Agreement Number %s is already used.', mou.agreement_number))

    @api.constrains('signed_date', 'expiry_date')
    def _check_dates(self):
        for mou in self:
            if mou.signed_date and mou.expiry_date and mou.expiry_date < mou.signed_date:
                raise ValidationError(_('Expiry Date must be after the Signed Date.'))

    def _require_manager(self):
        if not (self.env.su or self.env.user.has_group(MANAGER_GROUP)):
            raise AccessError(_('Only a Marketing Manager or Head can approve, sign, reject or renew an MOU.'))

    def write(self, vals):
        # Server-side guard: a plain edit/RPC write of `state` by an Executive
        # is refused. The proposal/review steps (open to Executives) and the
        # manager-only steps go through _set_state(), which sets the context flag.
        if 'state' in vals and not self.env.context.get('otm_mou_state_ok') \
                and not (self.env.su or self.env.user.has_group(MANAGER_GROUP)):
            raise AccessError(_('Use the MOU buttons to change the status.'))
        return super().write(vals)

    def _set_state(self, vals):
        return self.with_context(otm_mou_state_ok=True).write(vals)

    def action_send_proposal(self):
        self._set_state({'state': 'proposal_sent'})

    def action_under_review(self):
        self._set_state({'state': 'under_review'})

    def action_approve(self):
        self._require_manager()
        if any(m.state not in ('proposal_sent', 'under_review', 'discussion') for m in self):
            raise UserError(_('This MOU cannot be approved from its current status.'))
        self._set_state({'state': 'approved'})

    def action_sign(self):
        self._require_manager()
        for mou in self:
            if mou.state not in ('approved', 'renewed'):
                raise UserError(_('Only an approved MOU can be signed.'))
            if not mou.agreement_number or not mou.expiry_date:
                raise UserError(_('Enter the Agreement Number and Expiry Date before signing.'))
        self._set_state({'state': 'signed', 'signed_date': fields.Date.context_today(self)})
        for mou in self:
            text = self.env['otm.b2b.telegram.template']._render(
                'mou_signed', institution=mou.institution_id.name,
                agreement_number=mou.agreement_number or _('N/A'))
            if text:
                self.env['res.users']._otm_telegram_notify_heads(text)
                manager = mou.institution_id.marketing_manager_id
                if manager.otm_telegram_connected:
                    manager._otm_telegram_send(text)

    def action_reject(self):
        self._require_manager()
        self._set_state({'state': 'rejected'})

    def action_renew(self):
        self._require_manager()
        self._set_state({'state': 'renewed'})

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
            if mou.activity_ids.filtered(lambda a: a.summary == _('MOU Expiry Reminder')
                                         and a.date_deadline == mou.expiry_date):
                continue
            mou.activity_schedule(
                activity_type_id=activity_type.id if activity_type else False,
                summary=_('MOU Expiry Reminder'),
                note=_('MOU with %s expires on %s.', mou.institution_id.name, mou.expiry_date),
                date_deadline=mou.expiry_date,
                user_id=mou.institution_id.marketing_manager_id.id or self.env.uid,
            )
            manager = mou.institution_id.marketing_manager_id
            text = self.env['otm.b2b.telegram.template']._render(
                'mou_expiry', institution=mou.institution_id.name,
                date=fields.Date.to_string(mou.expiry_date))
            if text:
                if manager.otm_telegram_connected:
                    manager._otm_telegram_send(text)
                self.env['res.users']._otm_telegram_notify_heads(text)
