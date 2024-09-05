import datetime
from odoo import models, api


class ReportMaterialIssue(models.AbstractModel):
    _name = 'report.inno_finishing.report_print_jobwork_reissue'
    _description = 'Will prepare the data for displaying the template.'

    @api.model
    def _get_report_values(self, docids, data=None):
        record = self.env['finishing.baazar'].browse(docids)
        rec = record.jobwork_received_ids.filtered(lambda bl: bl.state == 'reject')
        prs = rec.mapped('product_id')
        division_id = prs.mapped("division_id")
        products = [{
            'barcode': ', '.join(
                (rec.filtered(lambda code: jobwork.id in code.product_id.ids)).barcode_id.mapped(
                    'name')),
            'design': jobwork.default_code, 'size': jobwork.inno_finishing_size_id.name,
            'pcs': len((rec.filtered(lambda code: jobwork.id in code.product_id.ids))),
            'cancel_pcs': '-', 'area': sum(
                (rec.filtered(lambda code: jobwork.id in code.product_id.ids)).mapped('total_area')),
            'rate': 1, 'inc': '-',
            'po_no': False
        } for jobwork in prs]
        data = {'company': {'company_name': record.finishing_work_id.company_id.name,
                            'logo': record.finishing_work_id.company_id.logo,
                            'address_line1': f"{record.finishing_work_id.company_id.street}, "
                                             f"{record.finishing_work_id.company_id.street}-"
                                             f"{record.finishing_work_id.company_id.zip}",
                            'address_line2': f"{record.finishing_work_id.company_id.city}, "
                                             f"({record.finishing_work_id.company_id.state_id.code}),"
                                             f"{record.finishing_work_id.company_id.country_id.name}",
                            'mobile': record.finishing_work_id.company_id.mobile,
                            'gstin': record.finishing_work_id.company_id.vat,
                            'state_code': record.finishing_work_id.company_id.state_id.code
                            },
                'subcontractor': {'name': record.subcontractor_id.name, 'address': record.subcontractor_id.street,
                                  'order_no': record.finishing_work_id.name,
                                  'city': record.subcontractor_id.city, 'date': datetime.datetime.today().date(),
                                  'contact_no': record.subcontractor_id.mobile or 'N/A',
                                  'reference' : record.reference,
                                  'due_date': record.finishing_work_id.expected_date,
                                  'aadhar_no': record.subcontractor_id.vat or 'N/A', 'issue_by': self.env.user.name
                                  },
                'products': {'data': products},
                'site': 'Main',
                'division': record.jobwork_received_ids.product_id[0].product_tmpl_id.division_id.name if
                record.jobwork_received_ids.product_id else 'N/A'
                }
        return {
            'doc_ids': docids,
            'doc_model': 'finishing.baazar',
            'docs': record,
            'data': data}