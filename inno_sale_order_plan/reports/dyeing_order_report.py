from odoo import models, api


class ReportDyeingPlan(models.AbstractModel):
    _name = 'report.inno_sale_order_plan.report_dyeing_order'
    _description = 'Dyeing Plan'

    @api.model
    def _get_report_values(self, docids, data=None):
        company = self.env['res.company'].search([], limit=1)
        record = self.env['dyeing.order'].browse(docids)
        shade_wise_summary = [{'shade': rec.name, 'qty': sum([line.quantity for line in record.dyeing_order_line_ids.filtered(lambda pd: pd.product_id.product_template_variant_value_ids.id == rec.id)])} for rec in record.dyeing_order_line_ids.product_id.product_template_variant_value_ids]
        yarn_wise_summary = [{'yarn': rec.name, 'qty': sum([line.quantity for line in record.dyeing_order_line_ids.filtered(lambda pd: pd.product_id.product_tmpl_id.id == rec.id)])} for rec in record.dyeing_order_line_ids.product_id.product_tmpl_id]
        sws1, sws2, sws3 = [], [], []
        while shade_wise_summary:
            try:
                sws1.append(shade_wise_summary.pop())
                sws2.append(shade_wise_summary.pop())
                sws3.append(shade_wise_summary.pop())
            except Exception as ex:
                pass
        data = {'s1': sws1, 's2': sws2, 's3': sws3, 'yarn_wise_summary': yarn_wise_summary,
                'subcontractor': {'name': record.partner_id.name, 'address': record.partner_id.street,
                                  'order_no': record.name,
                                  'city': record.partner_id.city, 'date': record.issue_date.strftime('%d/%m/%Y'),
                                  'contact_no': record.partner_id.mobile or 'N/A',
                                  'due_date': record.expected_date.strftime('%d/%m/%Y'),
                                  'aadhar_no': record.partner_id.vat or 'N/A', 'gen_by': self.env.user.name,
                                  'issue_by': self.env.user.employee_id.coach_id.name},
                'records': record.dyeing_order_line_ids, 'division': record.division_id.name}
        return {'doc_ids': docids, 'doc_model': 'dyeing.order', 'data': data, 'company': company}
