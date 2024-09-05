{
    "name": "Inno Data Migration",
    "version": "1.0.1",
    "summary": "Inno Data Migration",
    "depends": ['mrp', 'innorug_manufacture', 'inno_finishing'],
    "category": 'data',
    "data": [
        'data/ir_sequence.xml',
        'data/ir_cron.xml',
        'security/ir.model.access.csv',
        'views/view_migration_logs.xml',
        'views/view_migrate_operations.xml',
        'views/raw_materials_views.xml',
        'views/view_migration_record.xml',
        'views/view_stock_migration.xml',
        "views/update_mo_bom.xml",
        'menu/migration_menu.xml'
    ],
    'application': True,
    "installable": True,
    'license': 'LGPL-3',
}
