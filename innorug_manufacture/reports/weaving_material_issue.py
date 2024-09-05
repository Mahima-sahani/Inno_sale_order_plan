from datetime import datetime
from odoo import models, api,_
from odoo.exceptions import UserError, ValidationError, MissingError
from num2words import num2words
import logging

_logger = logging.getLogger(__name__)

class ReportPurchaseChallan(models.AbstractModel):
    _name = 'report.innorug_manufacture.report_weaving_material_issue'

    @api.model
    def _get_report_values(self, docids, data=None):

        product_quantities = {}
        docids = data.get('docids')
        subcontractor = data.get('subcontractor_id')
        records = (self.env['stock.picking'].browse(docids).
                   filtered(lambda rec: rec.picking_type_code == 'outgoing' and rec.state == 'done')) if \
            (data.get('report_type') == "weaving_material_issue") else \
            (self.env['stock.picking'].browse(docids).
             filtered(lambda rec: rec.picking_type_code == 'incoming' and rec.state == 'done'))
        materials_data = []
        for partner in records.partner_id:
            temp_data = dict()
            for move_line in records.filtered(lambda rec: rec.partner_id.id == partner.id).move_line_ids:
                prod_nam = f"{move_line.product_id.name} {move_line.product_id.product_template_variant_value_ids.name}"
                if prod_nam in temp_data.keys():
                    temp_data.get(prod_nam).update(
                        {'qty': temp_data.get(prod_nam).get('qty')+move_line.qty_done})
                else:
                    temp_data[prod_nam] = {
                        'product': move_line.product_id.name, 'qty': move_line.qty_done,
                        'shade': move_line.product_id.product_template_variant_value_ids.name}
            materials_data.append({'subcontractor': f"{partner.name} {str(partner.id)}" , 'data': [val for val in temp_data.values()],
                                   'gtotal': round(sum([rec.get('qty') for rec in temp_data.values()]), 3)})

        total_qty = sum(product_quantities.values())
        if data.get('report_type') == "weaving_material_issue":
            report_type = "Material Issue For Weaving"
        else:
            report_type = "Material Receive For Weaving"

        if data.get('subcontrctor_id'):
            type_report = "Party Wise Summary"
        elif data.get('from_date'):
            type_report = "Date Wise Summary"
        else:
            type_report = "General Summary"


        data = {
                'total_qty': total_qty,
                'report_type': report_type,
                'type_report': type_report,
                'subcontractor_id': subcontractor,
                'material_data': materials_data
            }
        report_data = {
            'doc_ids': docids,
            'doc_model': 'stock.picking',
            'docs': records,
            'data': data
        }

        return report_data
