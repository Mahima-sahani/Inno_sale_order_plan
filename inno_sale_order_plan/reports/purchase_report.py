from odoo import models, api


class ReportDyeingPlan(models.AbstractModel):
    _name = 'report.inno_sale_order_plan.report_purchase_material'
    _description = 'Dyeing Plan'

    @api.model
    def _get_report_values(self, docids, data=None):
        company = self.env['res.company'].search([], limit=1)
        record = self.env['inno.sale.order.planning'].browse(docids)
        purchase_data = dict()
        raw_material_group = ['acrlicy_yarn', 'polyster_yarn', 'jute_yarn', 'cotton_cone', 'silk', 'lefa', 'nylon',
                              'woolen_yarn', 'cotton_yarn', 'yarn']
        for rec in record.sale_order_id.mrp_production_ids.move_raw_ids:
            if rec.product_id.product_tmpl_id.raw_material_group not in raw_material_group:
                continue
            if rec.product_id.product_tmpl_id.with_shade:
                shade = rec.product_id.product_template_variant_value_ids.name
                if f"{rec.product_id.name} {shade}" not in purchase_data.keys():
                    purchase_data[f"{rec.product_id.name} {shade}"] = {'product': f"{rec.product_id.name} {shade}",
                                                                       'qty': rec.product_uom_qty,
                                                                       'unit': rec.product_id.uom_id.name,
                                                                       'category': rec.product_id.product_tmpl_id}
                else:
                    purchase_data.get(f"{rec.product_id.name} {shade}").update({'qty': purchase_data.get(f"{rec.product_id.name} {shade}").get('qty') + rec.product_uom_qty})
            else:
                if rec.product_id.product_tmpl_id.name not in purchase_data.keys():
                    purchase_data[rec.product_id.product_tmpl_id.name] = {'product': rec.product_id.product_tmpl_id.name,
                                                                          'qty': rec.product_uom_qty,
                                                                          'unit': rec.product_id.uom_id.name,
                                                                          'category': 'All'}
                else:
                    purchase_data.get(rec.product_id.product_tmpl_id.name).update(
                        {'qty': purchase_data.get(rec.product_id.product_tmpl_id.name).get('qty') + rec.product_uom_qty})
        categorise_data = dict()
        for data in purchase_data.values():
            if data.get('category') not in categorise_data.keys():
                categorise_data[data.get('category')] = [data]
            else:
                categorise_data.get(data.get('category')).append(data)
        data = {'records': categorise_data, 'pos': record.mapped('order_no')}
        return {'doc_ids': docids, 'doc_model': 'main.jobwork', 'data': data, 'company': company}