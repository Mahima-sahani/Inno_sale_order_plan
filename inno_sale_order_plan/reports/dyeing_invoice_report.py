from odoo import models, api, fields


class ReportDyeingMaterialIssue(models.AbstractModel):
    _name = 'report.inno_sale_order_plan.report_dyeing_invoice'
    _description = 'Dyeing Receive'

    @api.model
    def _get_report_values(self, docids, data=None):
        company = self.env['res.company'].search([], limit=1)
        record = self.env['inno.dyeing.receive'].browse(docids)
        data = {'subcontractor': {'name': record.partner_id.name, 'address': record.partner_id.street,
                                  'order_no': record.name,
                                  'city': record.partner_id.city, 'date': record.bill_id.invoice_date.strftime('%d/%m/%Y'),
                                  'contact_no': record.partner_id.mobile or 'N/A', 'job_no': record.bill_id.name,
                                  'location': self.env.user.material_location_id.name,
                                  'aadhar_no': record.partner_id.vat or 'N/A', 'issue_by': self.env.user.name},
                'records': record.dyeing_receive_line_ids, 'remark': record.remark,
                'amount_total': record.bill_id.amount_total, 'amount_in_words': record.bill_id.amount_total_words,
                'taxes': record.bill_id.tax_totals.get('groups_by_subtotal').get('Untaxed Amount')}
        return {'doc_ids': docids, 'doc_model': 'inno.dyeing.receive', 'data': data, 'company': company}
