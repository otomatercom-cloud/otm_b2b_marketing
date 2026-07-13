# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class OtmB2bInstitution(models.Model):
    """Master record for a School / College / University / Training Centre
    that Marketing Executives visit and nurture as a B2B account."""
    _name = 'otm.b2b.institution'
    _description = 'B2B Institution'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'
    _rec_name = 'name'

    # ---------------------------------------------------------------
    # Identification
    # ---------------------------------------------------------------
    code = fields.Char(string='Institution Code', copy=False, readonly=True,
                        default=lambda self: _('New'))
    name = fields.Char(string='Institution Name', required=True, tracking=True, index=True)
    institution_type_id = fields.Many2one(
        'otm.b2b.institution.type', string='Institution Type',
        required=True, tracking=True)
    university_id = fields.Many2one('otm.b2b.university', string='University', tracking=True)
    zone_id = fields.Many2one('otm.b2b.zone', string='Zone', tracking=True)
    tier_id = fields.Many2one('otm.b2b.tier', string='Category / Tier', tracking=True)
    tag_ids = fields.Many2many('otm.b2b.tag', string='Tags')

    # ---------------------------------------------------------------
    # Address / Geo
    # ---------------------------------------------------------------
    street = fields.Char(string='Address')
    street2 = fields.Char(string='Address Line 2')
    city = fields.Char(string='City')
    location = fields.Char(string='Location', help='Landmark, area, or map link')
    district = fields.Selection([
        ('thiruvananthapuram', 'Thiruvananthapuram'),
        ('kollam', 'Kollam'),
        ('pathanamthitta', 'Pathanamthitta'),
        ('alappuzha', 'Alappuzha'),
        ('kottayam', 'Kottayam'),
        ('idukki', 'Idukki'),
        ('ernakulam', 'Ernakulam'),
        ('thrissur', 'Thrissur'),
        ('palakkad', 'Palakkad'),
        ('malappuram', 'Malappuram'),
        ('kozhikode', 'Kozhikode'),
        ('wayanad', 'Wayanad'),
        ('kannur', 'Kannur'),
        ('kasaragod', 'Kasaragod'),
    ], string='District')
    state_id = fields.Many2one('res.country.state', string='State')
    country_id = fields.Many2one('res.country', string='Country',
                                  default=lambda self: self.env.ref('base.in', raise_if_not_found=False))
    zip = fields.Char(string='Pincode')
    partner_latitude = fields.Float(string='Latitude', digits=(16, 6))
    partner_longitude = fields.Float(string='Longitude', digits=(16, 6))

    # ---------------------------------------------------------------
    # Key contacts (quick-access denormalized fields; full list in contact_ids)
    # ---------------------------------------------------------------
    principal_name = fields.Char(string='Principal Name')
    principal_mobile = fields.Char(string='Principal Mobile')
    vice_principal_name = fields.Char(string='Vice Principal')
    management_contact_name = fields.Char(string='Management Contact')
    placement_officer_name = fields.Char(string='Placement Officer')
    admission_officer_name = fields.Char(string='Admission Officer')
    counsellor_name = fields.Char(string='Counsellor')
    decision_maker = fields.Char(string='Decision Maker')
    hod_name = fields.Char(string='HOD Name')
    hod_mobile = fields.Char(string='HOD Contact')
    supporting_staff_name = fields.Char(string='Supporting Staff Name')
    supporting_staff_mobile = fields.Char(string='Supporting Staff Contact')
    phone = fields.Char(string='Office Phone')
    email = fields.Char(string='Email')
    website = fields.Char(string='Website')

    # ---------------------------------------------------------------
    # Academic strength
    # ---------------------------------------------------------------
    student_strength = fields.Integer(string='Student Strength')
    plus_two_strength = fields.Integer(string='Plus Two Strength')
    final_year_strength = fields.Integer(string='Final Year Students')
    second_year_strength = fields.Integer(string='Second Year Students')
    first_year_strength = fields.Integer(string='First Year Students')
    ug_strength = fields.Integer(string='UG Strength')
    pg_strength = fields.Integer(string='PG Strength')
    commerce_strength = fields.Integer(string='Commerce Strength')
    science_strength = fields.Integer(string='Science Strength')
    humanities_strength = fields.Integer(string='Humanities Strength')
    placement_strength = fields.Integer(string='Placement Strength')
    courses_offered = fields.Text(string='Courses Offered')

    # ---------------------------------------------------------------
    # Status / ownership
    # ---------------------------------------------------------------
    status = fields.Selection([
        ('new', 'New'),
        ('active', 'Active'),
        ('inactive', 'Inactive'),
        ('blacklisted', 'Blacklisted'),
    ], string='Status', default='new', required=True, tracking=True)
    remarks = fields.Text(string='Remarks')
    marketing_manager_id = fields.Many2one(
        'res.users', string='Assigned Marketing Manager', tracking=True,
        default=lambda self: self.env.user)
    user_id = fields.Many2one(
        'res.users', string='Salesperson', default=lambda self: self.env.user)
    company_id = fields.Many2one(
        'res.company', string='Company', required=True,
        default=lambda self: self.env.company)
    active = fields.Boolean(string='Active', default=True)

    # ---------------------------------------------------------------
    # Relations
    # ---------------------------------------------------------------
    contact_ids = fields.One2many('otm.b2b.institution.contact', 'institution_id', string='Contacts')
    visit_plan_ids = fields.One2many('otm.b2b.visit.plan', 'institution_id', string='Visit Plans')
    visit_record_ids = fields.One2many('otm.b2b.visit.record', 'institution_id', string='Visit Records')
    lead_ids = fields.One2many('otm.b2b.lead', 'institution_id', string='Leads')
    seminar_ids = fields.One2many('otm.b2b.seminar', 'institution_id', string='Seminars')
    mou_ids = fields.One2many('otm.b2b.mou', 'institution_id', string='MOUs')

    # ---------------------------------------------------------------
    # Computed KPIs (Automatic Features)
    # ---------------------------------------------------------------
    visit_count = fields.Integer(string='Visit Count', compute='_compute_visit_stats')
    total_visits = fields.Integer(string='Total Visits', compute='_compute_visit_stats', store=True)
    first_visit_date = fields.Date(string='First Visit Date', compute='_compute_visit_stats', store=True)
    last_visit_date = fields.Date(string='Last Visit Date', compute='_compute_visit_stats', store=True)
    days_since_last_visit = fields.Integer(string='Days Since Last Visit', compute='_compute_visit_stats')
    upcoming_visit_date = fields.Date(string='Upcoming Visit', compute='_compute_visit_stats', store=True)

    contact_count = fields.Integer(string='Contact Count', compute='_compute_related_counts', store=True)
    seminar_count = fields.Integer(string='Seminar Count', compute='_compute_related_counts', store=True)
    lead_count = fields.Integer(string='Lead Count', compute='_compute_related_counts', store=True)
    mou_count = fields.Integer(string='MOU Count', compute='_compute_related_counts', store=True)
    total_leads_collected = fields.Integer(string='Total Leads Collected', compute='_compute_related_counts', store=True)
    total_seminars = fields.Integer(string='Total Seminars', compute='_compute_related_counts', store=True)
    total_mous = fields.Integer(string='Total MOUs', compute='_compute_related_counts', store=True)
    mou_signed = fields.Boolean(string='Has Signed MOU', compute='_compute_related_counts', store=True)

    # Quick-view snapshot of the latest visit and latest MOU, so the
    # institution form mirrors a flat spreadsheet view without duplicating
    # the actual data entry (source of truth stays on Visit Record / MOU).
    last_marketing_activity_id = fields.Many2one(
        'otm.b2b.activity.type', string='Marketing Activity',
        compute='_compute_last_visit_snapshot', store=True)
    last_visit_remarks = fields.Text(string='Visit Remarks', compute='_compute_last_visit_snapshot', store=True)
    last_visit_status = fields.Selection([
        ('draft', 'Draft'),
        ('completed', 'Completed'),
        ('partially_completed', 'Partially Completed'),
        ('cancelled', 'Cancelled'),
    ], string='Visit Status', compute='_compute_last_visit_snapshot', store=True)

    mou_type_id = fields.Many2one('otm.b2b.mou.type', string='MOU Type', compute='_compute_mou_snapshot', store=True)
    mou_status = fields.Selection([
        ('discussion', 'Discussion'),
        ('proposal_sent', 'Proposal Sent'),
        ('under_review', 'Under Review'),
        ('approved', 'Approved'),
        ('signed', 'Signed'),
        ('rejected', 'Rejected'),
        ('renewed', 'Renewed'),
    ], string='MOU Status', compute='_compute_mou_snapshot', store=True)
    mou_signed_date = fields.Date(string='MOU Signed Date', compute='_compute_mou_snapshot', store=True)
    mou_valid_till = fields.Date(string='MOU Valid Till', compute='_compute_mou_snapshot', store=True)
    mou_renewal_date = fields.Date(string='MOU Renewal Date', compute='_compute_mou_snapshot', store=True)

    _sql_constraints = [
        ('code_uniq', 'unique(code, company_id)', 'Institution Code must be unique per company.'),
    ]

    # ---------------------------------------------------------------
    # Compute methods
    # ---------------------------------------------------------------
    @api.depends('visit_record_ids.visit_date', 'visit_record_ids.state',
                 'visit_plan_ids.visit_date', 'visit_plan_ids.state')
    def _compute_visit_stats(self):
        today = fields.Date.context_today(self)
        for rec in self:
            visits = rec.visit_record_ids.filtered(lambda v: v.state != 'cancelled')
            dates = visits.mapped('visit_date')
            rec.visit_count = len(visits)
            rec.total_visits = len(visits)
            rec.first_visit_date = min(dates) if dates else False
            rec.last_visit_date = max(dates) if dates else False
            rec.days_since_last_visit = (today - rec.last_visit_date).days if rec.last_visit_date else 0
            upcoming = rec.visit_plan_ids.filtered(
                lambda p: p.state == 'planned' and p.visit_date and p.visit_date >= today
            ).sorted('visit_date')
            rec.upcoming_visit_date = upcoming[:1].visit_date if upcoming else False

    @api.depends('contact_ids', 'seminar_ids', 'lead_ids', 'mou_ids.state')
    def _compute_related_counts(self):
        for rec in self:
            rec.contact_count = len(rec.contact_ids)
            rec.seminar_count = len(rec.seminar_ids)
            rec.lead_count = len(rec.lead_ids)
            rec.mou_count = len(rec.mou_ids)
            rec.total_leads_collected = len(rec.lead_ids)
            rec.total_seminars = len(rec.seminar_ids)
            rec.total_mous = rec.mou_ids.filtered(lambda m: m.state == 'signed').__len__()
            rec.mou_signed = bool(rec.total_mous)

    @api.depends('visit_record_ids.visit_date', 'visit_record_ids.state',
                 'visit_record_ids.marketing_activity_type_id', 'visit_record_ids.remarks')
    def _compute_last_visit_snapshot(self):
        for rec in self:
            latest = rec.visit_record_ids.sorted('visit_date', reverse=True)[:1]
            rec.last_marketing_activity_id = latest.marketing_activity_type_id.id if latest else False
            rec.last_visit_remarks = latest.remarks if latest else False
            rec.last_visit_status = latest.state if latest else False

    @api.depends('mou_ids.state', 'mou_ids.discussion_date', 'mou_ids.signed_date',
                 'mou_ids.expiry_date', 'mou_ids.renewal_date', 'mou_ids.mou_type_id')
    def _compute_mou_snapshot(self):
        for rec in self:
            signed = rec.mou_ids.filtered(lambda m: m.state == 'signed').sorted('signed_date', reverse=True)[:1]
            latest = signed or rec.mou_ids.sorted('discussion_date', reverse=True)[:1]
            rec.mou_type_id = latest.mou_type_id.id if latest else False
            rec.mou_status = latest.state if latest else False
            rec.mou_signed_date = latest.signed_date if latest else False
            rec.mou_valid_till = latest.expiry_date if latest else False
            rec.mou_renewal_date = latest.renewal_date if latest else False

    # ---------------------------------------------------------------
    # CRUD
    # ---------------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('code', _('New')) == _('New'):
                vals['code'] = self.env['ir.sequence'].next_by_code('otm.b2b.institution') or _('New')
        return super().create(vals_list)

    # ---------------------------------------------------------------
    # Smart button actions
    # ---------------------------------------------------------------
    def action_view_visits(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'otm_b2b_marketing.action_otm_b2b_visit_record')
        action['domain'] = [('institution_id', '=', self.id)]
        action['context'] = {'default_institution_id': self.id}
        return action

    def action_view_seminars(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'otm_b2b_marketing.action_otm_b2b_seminar')
        action['domain'] = [('institution_id', '=', self.id)]
        action['context'] = {'default_institution_id': self.id}
        return action

    def action_view_leads(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'otm_b2b_marketing.action_otm_b2b_lead')
        action['domain'] = [('institution_id', '=', self.id)]
        action['context'] = {'default_institution_id': self.id}
        return action

    def action_view_mous(self):
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'otm_b2b_marketing.action_otm_b2b_mou')
        action['domain'] = [('institution_id', '=', self.id)]
        action['context'] = {'default_institution_id': self.id}
        return action

    def action_view_contacts(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _('Contacts'),
            'res_model': 'otm.b2b.institution.contact',
            'view_mode': 'list,form',
            'domain': [('institution_id', '=', self.id)],
            'context': {'default_institution_id': self.id},
        }

    # ---------------------------------------------------------------
    # Dashboard data (server-side scoping)
    # ---------------------------------------------------------------
    @api.model
    def get_dashboard_data(self):
        """Return every number the OWL dashboard needs, already scoped to
        the current user: a Marketing Executive only ever sees their own
        institutions/visits/leads here, matching the ir.rule restrictions
        already enforced elsewhere. Marketing Manager/Head see everything.
        Keeping this logic server-side (rather than duplicated per-call in
        JS) is both more secure and immune to client ORM API churn."""
        is_manager = self.env.user.has_group('otm_b2b_marketing.group_otm_b2b_marketing_manager')
        uid = self.env.uid
        today = fields.Date.context_today(self)

        institution_domain = []
        visit_plan_domain = []
        visit_record_domain = []
        if not is_manager:
            institution_domain = ['|', ('marketing_manager_id', '=', uid), ('user_id', '=', uid)]
            visit_plan_domain = [('user_id', '=', uid)]
            visit_record_domain = [('user_id', '=', uid)]

        Institution = self.env['otm.b2b.institution']
        institutions = Institution.search(institution_domain)
        institution_ids = institutions.ids

        lead_domain = [('institution_id', 'in', institution_ids)] if not is_manager else []
        seminar_domain = [('institution_id', 'in', institution_ids)] if not is_manager else []
        mou_domain = [('institution_id', 'in', institution_ids)] if not is_manager else []

        visit_plans = self.env['otm.b2b.visit.plan'].search(visit_plan_domain)
        today_visits = len(visit_plans.filtered(lambda p: p.visit_date == today))
        upcoming_plans = visit_plans.filtered(
            lambda p: p.state == 'planned' and p.visit_date and p.visit_date >= today
        ).sorted('visit_date')
        completed_visits = len(visit_plans.filtered(lambda p: p.state == 'completed'))
        pending_visits = len(visit_plans.filtered(lambda p: p.state in ('draft', 'planned', 'in_progress')))

        type_groups = Institution._read_group(
            institution_domain, groupby=['institution_type_id'], aggregates=['__count'])
        by_type = [
            {'label': inst_type.name if inst_type else _('Unspecified'), 'count': count}
            for inst_type, count in type_groups if count
        ]
        district_groups = Institution._read_group(
            institution_domain, groupby=['district'], aggregates=['__count'])
        district_labels = dict(Institution._fields['district'].selection)
        by_district = sorted(
            [{'label': district_labels.get(district, district) or _('Unspecified'), 'count': count}
             for district, count in district_groups if count],
            key=lambda row: row['count'], reverse=True,
        )[:6]

        upcoming_visit_list = [{
            'id': plan.id,
            'institution': plan.institution_id.name,
            'executive': plan.user_id.name,
            'district': district_labels.get(plan.institution_id.district, ''),
            'visit_date': fields.Date.to_string(plan.visit_date),
            'priority': plan.priority,
        } for plan in upcoming_plans[:5]]

        VisitRecord = self.env['otm.b2b.visit.record']
        live_visits = VisitRecord.search(
            visit_record_domain + [
                ('checkin_time', '!=', False),
                ('checkout_time', '=', False),
                ('state', 'not in', ('cancelled', 'completed')),
            ], order='checkin_time desc', limit=5)
        live_visit_list = [{
            'id': v.id,
            'institution': v.institution_id.name,
            'executive': v.user_id.name,
            'district': district_labels.get(v.institution_id.district, ''),
            'checkin_time': fields.Datetime.to_string(v.checkin_time) if v.checkin_time else '',
        } for v in live_visits]

        today_completed_visits = VisitRecord.search(
            visit_record_domain + [
                ('state', '=', 'completed'),
                ('visit_date', '=', today),
            ], order='checkout_time desc', limit=8)
        today_completed_list = [{
            'id': v.id,
            'institution': v.institution_id.name,
            'executive': v.user_id.name,
            'district': district_labels.get(v.institution_id.district, ''),
            'marketing_activity': v.marketing_activity_type_id.name or '',
        } for v in today_completed_visits]

        return {
            'is_manager': is_manager,
            'user_name': self.env.user.name,
            'cards': {
                'today_visits': today_visits,
                'upcoming_visits': len(upcoming_plans),
                'completed_visits': completed_visits,
                'pending_visits': pending_visits,
                'live_visits': len(live_visits),
                'today_completed': len(today_completed_visits),
                'institutions_assigned': Institution.search_count(
                    ['|', ('marketing_manager_id', '=', uid), ('user_id', '=', uid)]),
                'total_institutions': len(institutions),
                'new_institutions': len(institutions.filtered(lambda i: i.status == 'new')),
                'inactive_institutions': len(institutions.filtered(lambda i: i.status == 'inactive')),
                'leads_collected': self.env['otm.b2b.lead'].search_count(lead_domain),
                'seminars_conducted': self.env['otm.b2b.seminar'].search_count(seminar_domain),
                'mou_signed': self.env['otm.b2b.mou'].search_count(mou_domain + [('state', '=', 'signed')]),
            },
            'by_type': by_type,
            'by_district': by_district,
            'upcoming_visit_list': upcoming_visit_list,
            'live_visit_list': live_visit_list,
            'today_completed_list': today_completed_list,
        }
