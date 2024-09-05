{
    "name": "Inno Weaving Branch",
    "version": "15.1.1",
    "summary": "Weaving allotment to Branch",
    "description": "Add the feature to add the branch as a subcontractor.",
    "depends": ['mrp','innorug_manufacture'],
    "data": [
        'security/security.xml',
        'security/ir.model.access.csv',
        'data/ir_sequence.xml',
        'wizard/weaving_allotement.xml',
        'wizard/view_weaving_center_allotment.xml',
        'wizard/cancel_job_work.xml',
        'views/jobwork_allotment_views.xml',
        'views/weaving_branch_views.xml',
        'views/work_order_view.xml',
        'wizard/view_res_config_settings.xml',
        'views/view_main_job_work.xml',
        'menu/mrp_menu_views.xml',
    ],
    'application': True,
    "installable": True,
    'license': 'LGPL-3',
}


