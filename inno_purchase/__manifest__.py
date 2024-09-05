{
    "name": "Inno Purchase",
    "version": "16.1.1",
    "summary": "Purchase",
    "description": "Will help to manage the purchase.",
    "depends": ['mrp', 'innorug_manufacture', 'inno_default_config','stock', 'inno_sale_order_plan'],
    "data": [
        'security/ir.model.access.csv',
        'views/inno_purchase_views.xml',
        'data/ir_sequenxe.xml',
        "views/stock_picking_views.xml",
        "views/account_move_views.xml",
        "views/views_purchase_order.xml",
        "views/receive_products_views.xml",
        "views/mrp_views.xml",
        "views/vendor_material_issue_views.xml",
        "wizard/inno_receive_wizard_views.xml",
        "wizard/view_res_config_settings.xml",
        "wizard/report_wiz.xml",
        'wizard/vendor_material_wizard.xml',
        "report/purchase_order_report.xml",
        "report/vendor_material_report.xml",
        "report/purchase_challan_report.xml",
        "report/credit_note_report.xml",
        "report/purchase_indent_report.xml",
        'report/purchase_invoice_report.xml',
        'report/carpet_purchase_order.xml',
        "report/carpet_purchase_challan.xml",
        "report/carpet_purchase_invoice.xml",
        "report/purchase_order_balance.xml",
        'menu/menu.xml',
    ],
    'application': True,
    "installable": True,
    'license': 'LGPL-3',
}
