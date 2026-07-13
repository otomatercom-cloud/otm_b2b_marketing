# -*- coding: utf-8 -*-
{
    'name': 'B2B Marketing - Logic School Of Management',
    'version': '19.0.1.0.0',
    'category': 'Marketing',
    'summary': 'B2B institutional marketing, visit tracking and lead management for '
               'educational institutions',
    'description': """
B2B Marketing - Logic School Of Management
=============================================
A proprietary module built by Otomater for Logic School Of Management, for
managing B2B Marketing activities with Schools, Colleges, Universities,
Coaching Centres and Training Institutes.

Features
--------
* Institution database with full contact and academic-strength profile
* Visit planning and visit record tracking with GPS check-in/check-out
* Lead collection during institutional visits
* Seminar and event management
* MOU (Memorandum of Understanding) lifecycle tracking
* Multi-level security: Marketing Executive / Manager / Head
* OWL dashboard with KPI cards and charts
* Reports: visit, executive performance, lead, seminar, MOU
""",
    'author': 'Otomater',
    'company': 'Logic School Of Management',
    'website': 'https://otomater.com',
    'license': 'OPL-1',
    'depends': ['base', 'mail', 'web'],
    'data': [
        # security
        'security/otm_b2b_marketing_security.xml',
        'security/ir.model.access.csv',
        # data
        'data/otm_b2b_sequence_data.xml',
        'data/otm_b2b_institution_type_data.xml',
        'data/otm_b2b_activity_type_data.xml',
        'data/otm_b2b_masters_data.xml',
        'data/otm_b2b_cron_data.xml',
        # wizard
        'wizard/otm_b2b_assign_manager_wizard_views.xml',
        'wizard/otm_b2b_visit_complete_wizard_views.xml',
        # views
        'views/otm_b2b_institution_type_views.xml',
        'views/otm_b2b_activity_type_views.xml',
        'views/otm_b2b_tag_views.xml',
        'views/otm_b2b_masters_views.xml',
        'views/otm_b2b_institution_views.xml',
        'views/otm_b2b_visit_plan_views.xml',
        'views/otm_b2b_visit_record_views.xml',
        'views/otm_b2b_lead_views.xml',
        'views/otm_b2b_seminar_views.xml',
        'views/otm_b2b_mou_views.xml',
        'views/otm_b2b_dashboard_views.xml',
        'views/otm_b2b_report_views.xml',
        'views/otm_b2b_portal_templates.xml',
        # reports (QWeb)
        'report/otm_b2b_visit_report_templates.xml',
        'report/otm_b2b_mou_report_templates.xml',
        'report/otm_b2b_report_actions.xml',
        # menus (last: needs every action id above to already exist)
        'views/otm_b2b_menus.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'otm_b2b_marketing/static/src/js/otm_b2b_dashboard.js',
            'otm_b2b_marketing/static/src/xml/otm_b2b_dashboard.xml',
            'otm_b2b_marketing/static/src/css/otm_b2b_dashboard.css',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'post_init_hook': 'post_init_hook',
}
