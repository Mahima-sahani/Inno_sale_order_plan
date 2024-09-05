import datetime
from odoo import models, api
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ReportPurchaseOrderBalance(models.AbstractModel):
    _name = 'report.inno_purchase.report_purchase_order_balance'
    _description = 'Purchase Order Balance Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        
        docids = data.get('docids')
        to_date = data.get('to_date')
        from_date = data.get('from_date')
        records = self.env['purchase.order'].browse(docids).sorted(lambda d: d.date_order).filtered(lambda rec: rec.order_type == "carpet")
        total_order_qty = []
        total_balance_qty = []
        total_balance_deal = []
        total_balance_amount = []

        for order_line in records.order_line:
            total_order_qty.append(order_line.product_qty)
            total_balance_qty.append(order_line.product_qty - order_line.qty_received)

            bal_qty = order_line.product_qty - order_line.qty_received
            bal_qty_deal = (float(order_line.total_area)/float(order_line.product_qty) * float(bal_qty))
            total_balance_deal.append(float(bal_qty_deal))

            bal_amt = float(order_line.product_qty) - float(order_line.qty_received)
            balance_amount = float(order_line.price_unit) * float(bal_amt)
            total_balance_amount.append(balance_amount)

        if not records:
            raise UserError("Records does not found")
        data = {
            'total_order_qty' : sum(total_order_qty),
            'total_balance_qty' : sum(total_balance_qty),
            'total_balance_deal' : sum(total_balance_deal),
            'total_balance_amount' : sum(total_balance_amount),
            'to_date': to_date,
            'from_date': from_date
        }
        return {
            'doc_ids': docids,
            'doc_model': 'inno.sale.order.planning',
            'docs': records,
            'data': data
        }
