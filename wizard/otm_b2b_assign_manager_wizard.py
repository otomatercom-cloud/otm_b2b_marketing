# -*- coding: utf-8 -*-
from odoo import api, fields, models


class OtmB2bAssignManagerWizard(models.TransientModel):
    """Bulk-assign a Marketing Manager/Executive to a selection of institutions."""
    _name = 'otm.b2b.assign.manager.wizard'
    _description = 'Bulk Assign Marketing Manager'

    institution_ids = fields.Many2many('otm.b2b.institution', string='Institutions', required=True)
    marketing_manager_id = fields.Many2one('res.users', string='Marketing Manager', required=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        if self.env.context.get('active_model') == 'otm.b2b.institution':
            res['institution_ids'] = [(6, 0, self.env.context.get('active_ids', []))]
        return res

    def action_apply(self):
        self.ensure_one()
        self.institution_ids.write({'marketing_manager_id': self.marketing_manager_id.id})
        return {'type': 'ir.actions.act_window_close'}
