from odoo import models, api, fields


class ReportDyeingMaterialIssue(models.AbstractModel):
    _name = 'report.inno_sale_order_plan.report_dyeing_receive'
    _description = 'Dyeing Receive'

    @api.model
    def _get_report_values(self, docids, data=None):
        company = self.env['res.company'].search([], limit=1)
        record = self.env['inno.dyeing.receive'].browse(docids)
        data = {'subcontractor': {'name': record.partner_id.name, 'address': record.partner_id.street,
                                  'order_no': record.name,
                                  'city': record.partner_id.city, 'date': record.receive_date.strftime('%d/%m/%Y'),
                                  'contact_no': record.partner_id.mobile or 'N/A', 'job_no': record.job_worker_doc,
                                  'location': self.env.user.material_location_id.name,
                                  'aadhar_no': record.partner_id.vat or 'N/A', 'issue_by': self.env.user.name},
                'records': record.dyeing_receive_line_ids, 'remark': record.remark}
        return {'doc_ids': docids, 'doc_model': 'inno.dyeing.receive', 'data': data, 'company': company}
