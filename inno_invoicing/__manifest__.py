{
    "name": "Inno Invoicing",
    "version": "16.1.1",
    "summary": "Invoicing Process.",
    "description": """
                    Invoice finishing product to deliver.
                    """,
    "depends": ['sale_stock','inno_packaging','innorug_manufacture','report_xlsx',],
    "data": ['security/ir.model.access.csv',
             'data/ir_sequence.xml',
             'data/paper_formate.xml',
             'views/inno_packaging_views.xml',
             'views/inherit_pakaging_views.xml',
             'wizards/report_wizard_views.xml',
             'reports/cargo_reports.xml',
             'reports/export_invoice.xml',
             'reports/order_sheet_report.xml',
            'reports/report_xlsx.xml',
             'menu/menu.xml',],
    'application': True,
    "installable": True,
    'license': 'LGPL-3',
}