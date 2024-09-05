{
    "name" : "InnoRug Manufacturing",
    "depends": ['mrp','sale','stock','product','account',"hr_contract",'mail', 'inno_default_config', 'contacts',],
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequenxe.xml",
        "data/paperformat.xml",
        "data/ir_cron.xml",
        "reports/gate_pass_reports.xml",
        "reports/allotment_product_report.xml",
        "reports/barcode_report.xml",
        "reports/custom_header_template.xml",
        "reports/material_issue.xml",
        "reports/jobwork_reissue.xml",
        "reports/gate_pass_reports.xml",
        "reports/bazaar_receiving_report.xml",
        "reports/jobwork_cancellation_report.xml",
        "reports/cost_center_report.xml",
        "reports/weaving_order_status.xml",
        "reports/to_be_issue.xml",
        "reports/weaving_bazar_receipt.xml",
        "reports/weaving_order_barcode_balance_for_inspection.xml",
        "reports/baazar_receiving_size_wise_reports.xml",
        "reports/weaving_payment_bill_report.xml",
        "reports/weaving_payment_advice_report.xml",
        "reports/tds_advice_report.xml",
        "wizards/weaving_allotement.xml",
        "reports/weaving_material_issue.xml",
        "reports/weaving_material_issue_summary.xml",
        "reports/weaving_material_issue_date_wise.xml",
        "reports/weaving_material_issue_wise.xml",
        "reports/check_details.xml",
        "reports/weaving_order_report.xml",
        "reports/material_on_loom.xml",
        'wizards/view_res_config_settings.xml',
        "wizards/regenereate_barcodess.xml",
        "wizards/view_amend_return_wiz.xml",
        "wizards/view_cancel_jobwork.xml",
        "wizards/gate_pass_verification.xml",
        "wizards/inno_size_wizard_views.xml",
        "wizards/view_bazaar_incentive.xml",
        "wizards/view_barcode_scanning.xml",
        "wizards/view_update_expected_date.xml",
        "wizards/view_barcode_info.xml",
        "wizards/view_ff_product_receive.xml",
        'wizards/view_sample_rate_udate.xml',
        'wizards/view_stock_transfer.xml',
        'views/work_order_view.xml',
        "views/mrp_production_views.xml",
        "views/mrp_bom_views.xml",
        # "views/wizard_views.xml",
        "views/sale_order.xml",
        "views/main_jobwork_views.xml",
        'views/main_baazar_views.xml',
        "views/mrp_divisions_views.xml",
        "views/mrp_pricelist_views.xml",
        "views/mrp_subcont_pricelist_views.xml",
        'views/mrp_barcode_view.xml',
        "views/product_views.xml",
        "views/mrp_quality_control_views.xml",
        "views/mrp_res_partner_views.xml",
        "views/view_api_requests.xml",
        "views/view_user_access.xml",
        "views/view_bazaar_lines.xml",
        "views/view_inno_rate_list.xml",
        'views/view_res_users.xml',
        'views/view_account_move.xml',
        'views/view_sku_product_mapper.xml',
        'views/view_pending_materials.xml',
        'views/view_stock_picking.xml',
        'wizards/view_update_cloth.xml',
        'wizards/view_report_wiz.xml',
        'views/view_inno_inventory.xml',
        'views/view_trace_map.xml',
        'views/mrp_menu_views.xml',
        # "wizards/mrp_sale_order.xml",
        
        # "views/sale_order.xml",
    ],
    'external_dependencies': {'python': ['python-barcode']},
    'application': True,
    "installable": True,
    'license': 'LGPL-3',
}

