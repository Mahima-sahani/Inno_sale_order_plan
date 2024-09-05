from datetime import datetime
from odoo import models, api,_
from odoo.exceptions import UserError, ValidationError, MissingError
from num2words import num2words
import logging

_logger = logging.getLogger(__name__)

class ReportPurchaseChallan(models.AbstractModel):
    _name = 'report.inno_purchase.carpet_purchase_challan'
    _description = 'Carpet Purchase Challan'

    @api.model
    def _get_report_values(self, docids, data=None):
        records = self.env['stock.picking'].browse(docids).filtered(lambda rec: rec.order_type == "carpet")
        doc_date = records.date_done.strftime("%d/%b/%Y") if records.date_done else False
        supplier_date = records.supplier_date.strftime("%d/%b/%Y") if records.supplier_date else False
        
        total_qty = []
        total_deal_qty = []
        serial_number = {}

        for index,stock_picking_line in enumerate(records.move_ids, start=1):
            serial_number[stock_picking_line.id] = index

            total_qty.append(stock_picking_line.product_uom_qty)
            
            # total_deal_qty.append(float(stock_picking_line.purchase_line_id.total_area))
            total_deal_qty.append(float(stock_picking_line.purchase_line_id.total_area)/float(stock_picking_line.purchase_line_id.product_qty))

        data = {
                'total_qty': sum(total_qty) if total_qty else False,
                'total_deal_qty': sum(total_deal_qty) if total_deal_qty else False,
                'serial_number': serial_number if serial_number else False,
                'doc_date':doc_date,
                'supplier_date':supplier_date
            }

        return {
            'doc_ids': docids,
            'doc_model': 'stock.picking',
            'docs': records,
            'data': data,
        }
