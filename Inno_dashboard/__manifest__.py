{
    "name": "Inno Dashboard",
    "version": "16.1.1",
    "summary": "InnoAge Analytical Dashboard",
    "depends": ['innorug_manufacture', 'board', 'web'],
    "category": 'OWL',
    "data": [
        'views/weaving_dashboard.xml'
    ],
    'application': True,
    "installable": True,
    'license': 'LGPL-3',
    'assets':{
        'web.assets_backend': [
            'Inno_dashboard/static/src/components/**/*.js',
            'Inno_dashboard/static/src/components/**/*.xml',
            'Inno_dashboard/static/src/components/**/*.scss',
        ]
    }
}
