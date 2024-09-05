from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

class ReportDyeingStatus(models.AbstractModel):
    _name = 'report.inno_sale_order_plan.report_dyeing_order_status'
    _description = 'Dyeing Order Status'

    @api.model
    def _get_report_values(self, docids, data=None):
        docids = data.get('docids')
        to_date = data.get('to_date')
        from_date = data.get('from_date')

        records = self.env['dyeing.order'].browse(docids)
        # print("--------------------------------------------------------------------",records[0].read())
        sorted_records = sorted(records, key=lambda rec: rec.issue_date)

        data = {
            'from_date': from_date,
            'to_date': to_date,
            'issue_date': {rec.id: rec.issue_date.strftime('%d-%b-%y') if rec.issue_date else '-' for rec in sorted_records},
            'order_no': [rec.name for rec in sorted_records],
            'due_days': {rec.id: (rec.expected_date - rec.issue_date).days if rec.expected_date and rec.issue_date else '-' for rec in sorted_records},
            'dyeing_house' :{rec.id: rec.partner_id.name for rec in sorted_records},
            'products': {},
            'total_received_qty': 0,
            'total_loss_qty': 0,
            'total_cancel_qty': 0,
            'total_quantity': 0, 
            'vendor': data.get('vendor'),
   
        }
        
        for rec in sorted_records:
            product_data = []
            for line in rec.dyeing_order_line_ids:
                product_data.append({
                    'product_id': line.product_id.name,
                    'quantity': line.quantity, 
                    'uom_id': line.uom_id.name, 
                    'received_qty': line.received_qty,
                    'cancel_qty': line.cancel_qty,
                    'loss_qty': line.loss_qty,
                    'design_id': line.design_id.name,
                    'shade': line.product_id.product_template_variant_value_ids.name,
                })
                data['total_received_qty'] += line.received_qty
                data['total_loss_qty'] += line.loss_qty
                data['total_cancel_qty'] += line.cancel_qty
                data['total_quantity'] += line.quantity

            data['products'][rec.id] = product_data

        report_data = {
            'doc_ids': docids,
            'doc_model': 'dyeing.order',
            'docs': sorted_records,
            'data': data
        }
        # _logger.info('Report data-------------------------------------------------: %s', report_data.get('data'))

        return report_data

