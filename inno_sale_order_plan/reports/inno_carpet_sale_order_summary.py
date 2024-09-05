
from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

class ReportCarpetSummary(models.AbstractModel):
    _name = 'report.inno_sale_order_plan.report_carpet_sale_order_summary'
    _description = 'Carpet Sale Order Report'

    @api.model
    def _get_report_values(self, docids, data=None):

        docids = data.get('docids')
        to_date = data.get('to_date')
        from_date = data.get('from_date')
        
        records = self.env['inno.sale.order.planning'].browse(data.get('docids'))
        # print("=======================================================================",records)
        # print(records.sale_order_planning_lines.product_id[0].mrp_area)
        
        recs = [{'name': rec.name, 'qty': sum(records.sale_order_planning_lines.
        filtered(lambda pl: pl.sale_order_planning_id.customer_name.id == rec.id).mapped('product_uom_qty')), 
        'area': sum([pr.mrp_area*sum(records.sale_order_planning_lines.filtered(lambda pl : pl.sale_order_planning_id.customer_name.id==rec.id 
        and pl.product_id.id==pr.id).mapped('product_uom_qty'))
        for pr in records.sale_order_planning_lines.product_id ]),
        'order_amount': sum(records.sale_order_planning_lines.filtered(lambda pl: pl.sale_order_planning_id.customer_name.id == rec.id)
        .mapped(lambda pl: pl.product_uom_qty * pl.rate)
        ),}
        for rec in records.customer_name]
        print(recs)

        # print("Size of recs list:====================================", len(recs))

        # for rec in recs:
        #    print("----------------------------------------------------",rec['name'])
        #    print("----------------------------------------------------",rec['qty'])

        # names = [rec['name'] for rec in recs]
        # print("----------------------------------------------------",names)
        # for name in names:
        #  print("-----------------------------------------------------------------------",name)

        # quantity = [rec['qty'] for rec in recs]
        # print("----------------------------------------------------",quantity)
        # for qty in quantity:
        #  print("-----------------------------------------------------------------------",qty)
                
        data = {
            'from_date': from_date,
            'to_date': to_date,
            'recs': recs,    
            
        }
        report_data = {
            'doc_ids': docids,
            'doc_model': 'inno.sale.order.planning',
            'docs': records,
            'data': data
        }
        _logger.info('Report data: %s', report_data)
        return report_data
