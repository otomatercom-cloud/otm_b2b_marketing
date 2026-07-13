# -*- coding: utf-8 -*-
from odoo import http, fields
from odoo.http import request


class OtmB2bPortalController(http.Controller):
    """Public, token-protected pages so a Marketing Executive can complete
    a visit from their phone without a backend login. This is a backup to
    the in-app 'Complete Visit' wizard, not a replacement for it - no
    'portal'/'website' module dependency, just a plain http.Controller
    route guarded by the record's own access_token."""

    def _get_visit(self, visit_id, token):
        visit = request.env['otm.b2b.visit.record'].sudo().browse(visit_id)
        if not visit.exists() or not token or visit.access_token != token:
            return None
        return visit

    @http.route('/b2b/visit/<int:visit_id>/<string:token>', type='http', auth='public', methods=['GET'])
    def visit_complete_form(self, visit_id, token, **kwargs):
        visit = self._get_visit(visit_id, token)
        if not visit:
            return request.not_found()
        activity_types = request.env['otm.b2b.activity.type'].sudo().search([])
        # Once a visit is completed the link is locked: re-opening it (or
        # re-POSTing to it) always shows the read-only confirmation screen,
        # never the editable form again, so a submitted update can't be
        # silently overwritten by re-visiting an old link.
        values = {
            'visit': visit,
            'activity_types': activity_types,
            'submitted': visit.state == 'completed',
        }
        return request.render('otm_b2b_marketing.portal_visit_complete_form', values)

    @http.route('/b2b/visit/<int:visit_id>/<string:token>/submit', type='http', auth='public', methods=['POST'])
    def visit_complete_submit(self, visit_id, token, **post):
        visit = self._get_visit(visit_id, token)
        if not visit:
            return request.not_found()

        if visit.state != 'completed':
            now = fields.Datetime.now()
            vals = {
                'remarks': post.get('remarks') or '',
                'next_action': post.get('next_action') or '',
                'state': 'completed',
                'checkout_time': visit.checkout_time or now,
            }
            if not visit.checkin_time:
                vals['checkin_time'] = now
            activity_type_id = post.get('marketing_activity_type_id')
            if activity_type_id:
                vals['marketing_activity_type_id'] = int(activity_type_id)
            next_followup_date = post.get('next_followup_date')
            if next_followup_date:
                vals['next_followup_date'] = next_followup_date
            visit.sudo().write(vals)

            if visit.visit_plan_id and visit.visit_plan_id.state != 'completed':
                visit.visit_plan_id.sudo().write({'state': 'completed'})
        # else: already completed - this is a resubmission of a locked
        # link (double-tap, back-button, or a stale bookmark). Skip the
        # write entirely and just show the same locked confirmation, so a
        # second submit can never overwrite a first one.

        activity_types = request.env['otm.b2b.activity.type'].sudo().search([])
        values = {
            'visit': visit,
            'activity_types': activity_types,
            'submitted': True,
        }
        return request.render('otm_b2b_marketing.portal_visit_complete_form', values)
