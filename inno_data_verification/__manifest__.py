{
    "name": "Inno Data Verification",
    "version": "16.1.1",
    "summary": "Data Verification",
    "description": "Will Verify all the data in the product.",
    "depends": ['sale', 'mrp', 'inno_sale_order_plan'],
    "data": [
        'security/security.xml',
        'security/ir.model.access.csv',
        'views/mrp_bom_views.xml',
             'views/view_product_verification.xml',
             'menu/menu.xml',
             'reports/data_verification_reprorts.xml'],
    'application': True,
    "installable": True,
    'license': 'LGPL-3',
}
