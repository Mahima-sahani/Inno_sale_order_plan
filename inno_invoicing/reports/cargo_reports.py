import datetime
from odoo import models, api


class ReportCargo(models.AbstractModel):
    _name = 'report.inno_invoicing.report_print_cargo_reports'
    _description = 'Will prepare the data for displaying the template.'


    def company_details(self):
        pass

    @api.model
    def _get_report_values(self, docids, data=None):
        print("kkkkkkkkkkkkkkkkkkkkk")
        record = self.env['inno.packaging'].browse(docids)
        cargo_recs = [{
            'shipper': "rishabh",
            # 'consignee': bazaar_line.product_id.product_tmpl_id.name, 'place_of_receipt': bazaar_line.product_id.inno_mrp_size_id.name,
            # 'port_of_loading': bazaar_line.product_id.mrp_area, 'port_of_discharge': bazaar_line.job_work_id.rate,
            # 'place_of_delivery': bazaar_line.job_work_id.mrp_work_order_id.sale_id.name, 'container_no' : '', 'seal_no' : '', 'shipping_billing_no' : '', 'cargo_marks_no': '',
            # 'rolls_range' : '', 'no_type_pkg' : '', 'full_desc' : '', 'gross_weight' : '', 'hts' : '', 'place_cargo_dcl' : '', 'date_of_issue' : '', 'name_shipper' : '',
        }
            # for bazaar_line in record.baazar_lines_ids.filtered(lambda bl: bl.state == 'reject')
        ]
        data = {
                'recs': {'data': cargo_recs},
                }
        return {
            'doc_ids': docids,
            'doc_model': 'inno.packaging',
            'docs': record,
            'data': data}