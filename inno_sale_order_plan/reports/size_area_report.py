from odoo import models, api


class ReportDyeingPlan(models.AbstractModel):
    _name = 'report.inno_sale_order_plan.report_size_area'
    _description = 'Dyeing Plan'

    @api.model
    def _get_report_values(self, docids, data=None):
        company = self.env['res.company'].search([], limit=1)
        record = self.env['inno.sale.order.planning'].browse(docids)
        size_data = []
        for design in record.sale_order_planning_lines.product_id.product_tmpl_id:
            size_data_list = []
            for line in record.sale_order_planning_lines.filtered(
                    lambda pl: pl.product_id.product_tmpl_id.id == design.id):
                size_data_list.append(
                    {'product': line.product_id.default_code, 'size': line.product_id.inno_mrp_size_id.name,
                     'area': line.product_id.mrp_area, 'qty': line.manufacturing_qty,
                     'total_area': line.product_id.mrp_area * line.manufacturing_qty, })
            size_data.append({'design': design.name, 'data': size_data_list, 'quality': design.quality.name})
        data = {'records': size_data, 'order_no': f"{record.order_no} / {record.sale_order_id.name}",
                'date': f"{record.order_date.strftime('%d/%b/%Y') if record.order_date else False} to {record.due_date.strftime('%d/%b/%Y') if record.due_date else False}"}
        return {'doc_ids': docids, 'doc_model': 'main.jobwork', 'data': data, 'company': company}
