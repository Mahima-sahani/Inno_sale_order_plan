import datetime
from odoo import models, api,_
from odoo.exceptions import UserError, ValidationError, MissingError
import logging

_logger = logging.getLogger(__name__)

class ReportMaterialIssue(models.AbstractModel):
    _name = 'report.inno_finishing.report_order_balance_reports_report'
    _description = 'Will Provide the report Order Balance reports'

    @api.model
    def _get_report_values(self, docids, data=None):

        docids = data.get('docids')
        to_date = data.get('to_date')
        from_date = data.get('from_date')
        process = data.get('process')
        records = self.env['jobwork.barcode.line'].browse(docids)
        vendors = records.finishing_work_id.subcontractor_id
        data = []
        for rec in vendors:
            vend = {rec.name: []}
            lines = records.filtered(lambda rs: rs.finishing_work_id.subcontractor_id.id in rec.ids)
            order = lines.finishing_work_id
            ven_list = []
            for ord in order:
                order_wise = lines.filtered(lambda rs: rs.finishing_work_id.id in ord.ids)
                product = order_wise.product_id
                for prod in product:
                    ven_list.append({
                        'order_date' : ord.issue_date.strftime("%d/%b/%y"),
                        'order_no' : ord.name,
                        'quality' : prod.product_tmpl_id.quality.name,
                        'design' : prod.product_tmpl_id.name,
                        'size' : prod.inno_finishing_size_id.name,
                        'pcs' : order_wise.filtered(lambda ar: ar.product_id.id in prod.ids).__len__(),
                        'area' : sum(order_wise.filtered(lambda ar: ar.product_id.id in prod.ids).mapped('total_area'))})
            
            vend[rec.name] = ven_list
            data.append(vend)

        subcontractor_totals = {}
        for rec in data:
            for subcontractor_name, subcontractor_data in rec.items():
                total_pcs = sum(entry['pcs'] for entry in subcontractor_data)
                total_area = sum(entry['area'] for entry in subcontractor_data)
                subcontractor_totals[subcontractor_name] = {'total_pcs': total_pcs, 'total_area': total_area}

        
        

        return {
            'doc_ids': docids,
            'doc_model': 'finishing.work.order',
            'docs': records,
            'data': data,
            'subcontractor_totals': subcontractor_totals,
            'to_date': to_date,
            'from_date': from_date,
            'process': process
            }
