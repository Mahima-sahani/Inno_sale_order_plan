{
    "name": "Inno Internet of Things",
    "version": "16.1.1",
    "summary": "IoT",
    "description": "Will help to manage the all the process required to finish the weaved products.",
    "depends": ['mrp', 'innorug_manufacture', 'inno_default_config'],
    "data": [
        'security/ir.model.access.csv',
             'views/barcode_scanner_views.xml',
             'menu/menu.xml',],
    'application': True,
    "installable": True,
    'license': 'LGPL-3',
}
