from odoo import models, api, fields


class ReportDyeingMaterialIssue(models.AbstractModel):
    _name = 'report.inno_sale_order_plan.report_dyeing_material_issue'
    _description = 'Dyeing Material Issue'

    @api.model
    def _get_report_values(self, docids, data=None):
        company = self.env['res.company'].search([], limit=1)
        record = self.env['dyeing.material.issue'].browse(docids)
        data = {'subcontractor': {'name': record.partner_id.name, 'address': record.partner_id.street,
                                  'order_no': record.name,
                                  'city': record.partner_id.city, 'date': fields.date.today().strftime('%d/%m/%Y'),
                                  'contact_no': record.partner_id.mobile or 'N/A',
                                  'location': self.env.user.material_location_id.warehouse_id.name,
                                  'aadhar_no': record.partner_id.vat or 'N/A', 'issue_by': self.env.user.name,
                                  'gate_pass_no': self.env['ir.sequence'].next_by_code('dyeing.material.gate_pass.seq')
                                  }, 'records': record.dyeing_material_issue_line_ids, 'remark': record.remark}
        return {'doc_ids': docids, 'doc_model': 'dyeing.material.issue', 'data': data, 'company': company}
