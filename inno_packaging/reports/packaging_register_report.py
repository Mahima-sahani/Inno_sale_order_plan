from datetime import datetime
from odoo import models, api,_
from odoo.exceptions import UserError, ValidationError, MissingError
import logging

_logger = logging.getLogger(__name__)

class ReportPackagingPosition(models.AbstractModel):
    _name = 'report.inno_packaging.report_packaging_register'

    @api.model
    def _get_report_values(self, docids, data=None):

        docids = data.get('docids')
        to_date = data.get('to_date')
        from_date = data.get('from_date')
        packaging_no = data.get('packaging_no')
        records = self.env['stock.quant'].browse(docids)
        total_qty = []
        total_area_sq = []
        total_area_ft = []
        new_data = []
        for rec in records:
            if rec.inno_package_id:
                prod_size = rec.product_id.product_template_variant_value_ids.name
                area = self.env['inno.size'].search([('name', '=', prod_size)])
                area_ft = area.area * int(rec.quantity) if area else 0
                
                total_qty.append(rec.quantity)
                total_area_sq.append(rec.area_sq_yard)
                total_area_ft.append(area_ft)

                new_data.append({'pack_date': rec.inno_package_id.packing_date.strftime('%d/%b/%y') if rec.inno_package_id.packing_date else False,
                                'pack_no': rec.inno_package_id.name,
                                'order_no': rec.inno_sale_id.order_no,
                                'bale_no': rec.roll_no,
                                'barcode': rec.barcode_id.name,
                                'prod_name': rec.product_id.default_code,
                                'prod_quality': rec.invoice_group_id.name,
                                'prod_tmpl': rec.product_id.product_tmpl_id.name,
                                'prod_size': rec.product_id.product_template_variant_value_ids.name,
                                'qty': rec.quantity,
                                'area_ft': area_ft,
                                'area_yard': rec.area_sq_yard})
            
        if not records:
            raise UserError("Record does not found") 
        report_data = {
            'doc_ids': docids,
            'doc_model': 'inno.packaging',
            'docs': records,
            'data': new_data,
            'total_qty': sum(total_qty),
            'total_area_sq': sum(total_area_sq),
            'total_area_ft': sum(total_area_ft),
            'to_date': to_date,
            'from_date': from_date,
            'packaging_no': packaging_no,
        }

        return report_data
