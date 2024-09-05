import datetime
from odoo import models, api


class ReportJobWorkReIssue(models.AbstractModel):
    _name = 'report.innorug_manufacture.report_print_jobwork_reissue'
    _description = 'Will prepare the data for displaying the template.'

    @api.model
    def _get_report_values(self, docids, data=None):
        record = self.env['main.baazar'].browse(docids)
        products = [{
            'barcode': bazaar_line.barcode.name,
            'design': bazaar_line.product_id.product_tmpl_id.name, 'size': bazaar_line.product_id.inno_mrp_size_id.name,
            'area': bazaar_line.product_id.mrp_area, 'rate': bazaar_line.job_work_id.rate,
            'po_no': bazaar_line.job_work_id.mrp_work_order_id.sale_id.name
        } for bazaar_line in record.baazar_lines_ids.filtered(lambda bl: bl.state == 'reject')]
        data = {'company': {'company_name': record.main_jobwork_id.company_id.name,
                            'logo': record.main_jobwork_id.company_id.logo,
                            'address_line1': f"{record.main_jobwork_id.company_id.street}, "
                                             f"{record.main_jobwork_id.company_id.street}-"
                                             f"{record.main_jobwork_id.company_id.zip}",
                            'address_line2': f"{record.main_jobwork_id.company_id.city}, "
                                             f"({record.main_jobwork_id.company_id.state_id.code}),"
                                             f"{record.main_jobwork_id.company_id.country_id.name}",
                            'mobile': record.main_jobwork_id.company_id.mobile,
                            'gstin': record.main_jobwork_id.company_id.vat,
                            'state_code': record.main_jobwork_id.company_id.state_id.code
                            },
                'subcontractor': {'name': record.subcontractor_id.name, 'address': record.subcontractor_id.street,
                                  'order_no': record.main_jobwork_id.reference,
                                  'purja_no': record.main_jobwork_id.cost_center,
                                  'city': record.subcontractor_id.city, 'date': datetime.datetime.today().strftime('%d/%m/%Y'),
                                  'contact_no': record.subcontractor_id.mobile or 'N/A',
                                  'due_date': record.main_jobwork_id.expected_received_date.strftime('%d/%m/%Y'),
                                  'aadhar_no': record.subcontractor_id.vat or 'N/A', 'issue_by': self.env.user.name
                                  },
                'products': {'data': products},
                'site': '-',
                'division': record.division_id.name if record.division_id.name else 'N/A'
                }
        return {
            'doc_ids': docids,
            'doc_model': 'main.baazar',
            'docs': record,
            'data': data}
