from datetime import datetime
from odoo import models, api,_
from odoo.exceptions import UserError, ValidationError, MissingError
import logging

_logger = logging.getLogger(__name__)

class ReportPackagingPosition(models.AbstractModel):
    _name = 'report.inno_packaging.report_packing_summary'

    @api.model
    def _get_report_values(self, docids, data=None):

        docids = data.get('docids')
        to_date = data.get('to_date')
        from_date = data.get('from_date')
        packaging_no = data.get('packaging_no')
        unit_area = data.get('unit_area')
        records = self.env['stock.quant'].browse(docids).filtered(lambda rec: rec.inno_package_id.status == 'progress')
        
        total_bale = []
        total_pcs = []
        total_area = []
        area_qty = 0.0
        pd_size = []

        data = []
        for product in records.product_id:
            product_size_id = product.product_template_variant_value_ids.id
            prod_size = product.product_template_variant_value_ids.name
            line_data = records.filtered(lambda rec: rec.product_id.product_template_variant_value_ids.name == prod_size)
            if prod_size not in pd_size:
                bale_no = line_data.mapped('roll_no')
                bale_count = len(set(bale_no))
                total_bale.append(bale_count)
                
                pcs = len(line_data)
                total_pcs.append(pcs)

                area = self.env['inno.size'].search([('name', '=', prod_size)])
                if unit_area == 'sq_feet':
                    area_qty = round(area.area * pcs,3)
                if unit_area == 'sq_meter':
                    area_qty = round(area.area_sq_mt * pcs,3)
                if unit_area == 'sq_yard':
                    area_qty = round(area.area_sq_yard * pcs,3)
                if unit_area == 'sq_cm':
                    area_qty = round(area.area_cm * pcs,3)
                total_area.append(area_qty)

                data.append({'prod_size': prod_size, 'pcs': pcs, 'bale': bale_count, 'area': area_qty})
            if prod_size not in pd_size:
                pd_size.append(prod_size)
        if not records:
            raise UserError("Record has been not found")
        
        if unit_area == 'sq_feet':
            unit = 'Area(Sq.Feet)'
        if unit_area == 'sq_meter':
            unit = 'Area(Sq.Meter)'
        if unit_area == 'sq_yard':
            unit = 'Area(Sq.Yard)'
        if unit_area == 'sq_cm':
            unit = 'Area(Sq.CM)'

        report_data = {
            'doc_ids': docids,
            'doc_model': 'inno.packaging',
            'docs': records,
            'data': data,
            'total_bale': sum(total_bale),
            'total_pcs': sum(total_pcs),
            'total_area': sum(total_area),
            'unit_area': unit_area,
            'unit_name': unit,
            'to_date': to_date,
            'from_date': from_date,
        }
        return report_data
