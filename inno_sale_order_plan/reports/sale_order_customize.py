import datetime
from odoo import models, api
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ReportMaterialIssue(models.AbstractModel):
    _name = 'report.inno_sale_order_plan.report_sale_order_customize'
    _description = 'Sale Order Customize Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        
        
        line_data = {}
        serial_number = {}
        total_order_qty = []
        total_order_amount = []
        overdue_days = {}
        # total_overdue_days = 0
        today = datetime.date.today()

        docids = data.get('docids')
        to_date = data.get('to_date')
        from_date = data.get('from_date')
        buyer = data.get('buyer')
        order_type = data.get('order_type')
        
        records = self.env['inno.sale.order.planning'].browse(docids).sorted(lambda rec: rec.order_date)

        for index, rec in enumerate(records.sale_order_planning_lines, start=1):
            due_date = rec.sale_order_planning_id.due_date
            if due_date:
                if today < due_date:
                    days_overdue = (today - due_date).days
                    overdue_days[rec.id] = days_overdue
                    # total_overdue_days+=days_overdue

                else:
                    days_overdue = (today - due_date).days
                    overdue_days[rec.id] = days_overdue
                    # total_overdue_days+=days_overdue

            total_order_qty.append(rec.product_uom_qty)
            total_order_amount.append(rec.total_amount)
            serial_number[rec.id] = index
        
        if not records:
            raise UserError("Record does not exist")

        data = {
            'data': [{'order_no': key, 'val': val} for key, val in line_data.items()],
            'serial_number': serial_number,
            'total_order_qty': sum(total_order_qty),
            'total_order_amount': sum(total_order_amount),
            'overdue_days': overdue_days,
            # 'total_overdue_days':total_overdue_days,
            'to_date': to_date,
            'from_date': from_date,
            'buyer': buyer,
            'order_type':order_type
        }

        return {
            'doc_ids': docids,
            'doc_model': 'inno.sale.order.planning',
            'docs': records,
            'data': data
        }
