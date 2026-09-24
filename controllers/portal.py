# -*- coding: utf-8 -*-
from itertools import zip_longest

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

    def _get_dashboard_url(self):
        """Direct link to the B2B Marketing dashboard itself, not just
        the generic Odoo apps home screen - built from the action's
        actual database id via its xmlid, so it stays correct no matter
        which database this is deployed to (never hardcode the numeric
        action id, that's assigned per-database and isn't portable)."""
        action = request.env.ref('otm_b2b_marketing.action_otm_b2b_dashboard', raise_if_not_found=False)
        action = action.sudo() if action else action
        return f'/odoo/action-{action.id}' if action else '/odoo'

    def _find_or_create_contact(self, institution, name, mobile):
        """Dedupe against the institution's existing contact directory
        (contact_ids on otm.b2b.institution) before creating a new one - by
        mobile number first (most reliable), falling back to a
        case-insensitive name match, so re-checking the same person's name
        on a second visit (instead of ticking the checkbox for them)
        doesn't pile up duplicate contact records. Returns a recordset of
        one otm.b2b.institution.contact, existing or newly created."""
        Contact = request.env['otm.b2b.institution.contact'].sudo()
        name = (name or '').strip()
        mobile = (mobile or '').strip()
        if not name:
            return Contact.browse()
        existing = institution.contact_ids
        match = Contact.browse()
        if mobile:
            match = existing.filtered(lambda c: c.mobile and c.mobile.strip() == mobile)
        if not match:
            match = existing.filtered(lambda c: c.name.strip().lower() == name.lower())
        if match:
            return match[:1]
        return Contact.create({
            'institution_id': institution.id,
            'name': name,
            'mobile': mobile,
        })

    def _parse_contact_ids(self, institution):
        """Combines (a) existing institution contacts ticked via checkbox
        and (b) newly typed name/mobile pairs (repeatable rows added by the
        page's own JS) into one list of otm.b2b.institution.contact ids to
        write onto the visit. New contacts are saved onto the institution's
        contact directory as they're created, so they show up as pickable
        options on this same institution's next visit too."""
        selected_ids = [int(i) for i in request.httprequest.form.getlist('contact_ids') if i]
        new_names = request.httprequest.form.getlist('new_contact_name')
        new_mobiles = request.httprequest.form.getlist('new_contact_mobile')
        contact_ids = set(selected_ids)
        for name, mobile in zip_longest(new_names, new_mobiles, fillvalue=''):
            contact = self._find_or_create_contact(institution, name, mobile)
            if contact:
                contact_ids.add(contact.id)
        return list(contact_ids)

    @http.route('/b2b/visit/<int:visit_id>/<string:token>', type='http', auth='public', methods=['GET'])
    def visit_complete_form(self, visit_id, token, **kwargs):
        visit = self._get_visit(visit_id, token)
        if not visit:
            return request.not_found()
        activity_types = request.env['otm.b2b.activity.type'].sudo().search([])
        # Existing contacts already on file for this institution (from this
        # or any earlier visit) - shown as a pick list so a repeat visit
        # doesn't require retyping someone who's already been logged.
        existing_contacts = visit.institution_id.sudo().contact_ids.sorted('name')
        # Once a visit is completed the link is locked: re-opening it (or
        # re-POSTing to it) always shows the read-only confirmation screen,
        # never the editable form again, so a submitted update can't be
        # silently overwritten by re-visiting an old link.
        values = {
            'visit': visit,
            'activity_types': activity_types,
            'existing_contacts': existing_contacts,
            'submitted': visit.state == 'completed',
            'dashboard_url': self._get_dashboard_url(),
        }
        return request.render('otm_b2b_marketing.portal_visit_complete_form', values)

    @http.route('/b2b/visit/<int:visit_id>/<string:token>/submit', type='http', auth='public', methods=['POST'])
    def visit_complete_submit(self, visit_id, token, **post):
        visit = self._get_visit(visit_id, token)
        if not visit:
            return request.not_found()

        if visit.state != 'completed':
            now = fields.Datetime.now()
            contact_ids = self._parse_contact_ids(visit.institution_id.sudo())
            vals = {
                'contact_ids': [(6, 0, contact_ids)],
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
        existing_contacts = visit.institution_id.sudo().contact_ids.sorted('name')
        values = {
            'visit': visit,
            'activity_types': activity_types,
            'existing_contacts': existing_contacts,
            'submitted': True,
            'dashboard_url': self._get_dashboard_url(),
        }
        return request.render('otm_b2b_marketing.portal_visit_complete_form', values)

    def _get_seminar(self, seminar_id, token):
        seminar = request.env['otm.b2b.seminar'].sudo().browse(seminar_id)
        if not seminar.exists() or not token or seminar.access_token != token:
            return None
        return seminar

    @http.route('/b2b/seminar/<int:seminar_id>/<string:token>', type='http', auth='public', methods=['GET'])
    def seminar_complete_form(self, seminar_id, token, **kwargs):
        seminar = self._get_seminar(seminar_id, token)
        if not seminar:
            return request.not_found()
        categories = request.env['otm.b2b.seminar.category'].sudo().search([])
        values = {
            'seminar': seminar,
            'categories': categories,
            'submitted': seminar.state == 'completed',
            'dashboard_url': self._get_dashboard_url(),
        }
        return request.render('otm_b2b_marketing.portal_seminar_complete_form', values)

    @http.route('/b2b/seminar/<int:seminar_id>/<string:token>/submit', type='http', auth='public', methods=['POST'])
    def seminar_complete_submit(self, seminar_id, token, **post):
        seminar = self._get_seminar(seminar_id, token)
        if not seminar:
            return request.not_found()

        if seminar.state != 'completed':
            now = fields.Datetime.now()
            # Checkboxes with the same name submit multiple values - only
            # available via the raw form, not the **post kwargs (which
            # collapses repeats to the last one).
            category_ids = [int(i) for i in request.httprequest.form.getlist('category_ids') if i]
            vals = {
                'topic': post.get('topic') or '',
                'category_ids': [(6, 0, category_ids)],
                'speaker': post.get('speaker') or '',
                'student_count': int(post.get('student_count') or 0),
                'faculty_count': int(post.get('faculty_count') or 0),
                'interested_students': int(post.get('interested_students') or 0),
                'feedback': post.get('feedback') or '',
                'outcome': post.get('outcome') or '',
                'state': 'completed',
                'checkout_time': seminar.checkout_time or now,
            }
            if not seminar.checkin_time:
                vals['checkin_time'] = now
            seminar.sudo().write(vals)

            if seminar.seminar_plan_id and seminar.seminar_plan_id.state != 'completed':
                seminar.seminar_plan_id.sudo().write({'state': 'completed'})
        # else: already completed - locked link resubmission, skip the
        # write entirely, same guarantee as the visit portal form.

        categories = request.env['otm.b2b.seminar.category'].sudo().search([])
        values = {
            'seminar': seminar,
            'categories': categories,
            'submitted': True,
            'dashboard_url': self._get_dashboard_url(),
        }
        return request.render('otm_b2b_marketing.portal_seminar_complete_form', values)
