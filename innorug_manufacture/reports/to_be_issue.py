from odoo import models, api


class ReportJobWorkReIssue(models.AbstractModel):
    _name = 'report.innorug_manufacture.report_weaving_to_be_issue'
    _description = 'Weaving To Be Issue'

    @api.model
    def _get_report_values(self, docids, data=None):
        company = self.env['res.company'].search([], limit=1)
        records = self.env['mrp.workorder'].sudo().browse(docids)
        data_prep = dict()
        grand_total_pcs = 0
        grand_total_area = 0
        for design in records.product_id.product_tmpl_id:
            total_pcs = 0
            total_area = 0
            temp_data = []
            for rec in records.filtered(lambda rec: rec.product_id.product_tmpl_id.id == design.id):
                temp_data.append({
                    'alloted_qty': rec.allotted_qty, 'remaining': rec.remaining_to_allocate,
                    'po_no': rec.sale_id.order_no if rec.sale_id else 'SAMPLE',
                    'order_date': rec.sale_id.date_order.date().strftime('%d-%b-%Y') if rec.sale_id else '-',
                    'due_date': rec.sale_id.validity_date.strftime('%d-%b-%Y') if rec.sale_id else '-',
                    'sku': rec.product_id.default_code, 'size': rec.product_id.product_template_attribute_value_ids.filtered(
                        lambda al: al.attribute_id.name == 'size').name, 'remaining_area': rec.remaining_to_allocate*rec.product_id.mrp_area})
                total_pcs += rec.remaining_to_allocate
                total_area += rec.remaining_to_allocate*rec.product_id.mrp_area
            if data:
                data_prep[design.name] = {'design': design.name, 'quality': design.quality.name, 'data': temp_data,
                                          'total_qty': total_pcs, 'total_area': total_area}
            grand_total_pcs += total_pcs
            grand_total_area += total_area
        data.update({'records': [data for data in data_prep.values()], 'grand_pcs': grand_total_pcs,
                     'grand_area': grand_total_area})
        return {'doc_ids': docids, 'doc_model': 'main.jobwork', 'data': data, 'company': company}
# sale.date_order.date().strftime('%d-%m-%Y')
