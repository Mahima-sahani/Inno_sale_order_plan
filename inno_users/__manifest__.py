{
    "name": "Inno Users Access",
    "version": "16.1.1",
    "summary": "Access",
    "description": "Will help to manage the users access.",
    "depends": ['mrp', 'innorug_manufacture',],
    "data": [
        "security/security.xml",
        'security/ir.model.access.csv',
        'views/user_access_views.xml',
        # 'menu/menu.xml',
    ],
    'application': True,
    "installable": True,
    'license': 'LGPL-3',
}
