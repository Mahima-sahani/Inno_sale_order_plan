from odoo import models, api
import logging
from datetime import datetime
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ReportWeavingBazar(models.AbstractModel):
    _name = 'report.innorug_manufacture.report_weaving_order'
    _description = 'Weaving Order Report'

    @api.model
    def _get_report_values(self, docids, data=None):

        total_pcs = []
        total_area = []
        total_rate = []
        total_incentive = []
        docids = data.get('docids')
        to_date = data.get('to_date')
        from_date = data.get('from_date')
        division = data.get('division')
        product = data.get('product')
        new_data = []
        weavng_wise_report = data.get('weavng_wise_report', False)
        if weavng_wise_report:
            weavng_wise_report = "Design Wise Report"
        else:
            weavng_wise_report = "Product Wise Report"

        records = self.env['mrp.job.work'].browse(docids).filtered(lambda rec: rec.main_jobwork_id.state not in ["cancel"])
        
        for rec in records:
            
            if weavng_wise_report == "Design Wise Report":
                product = rec.product_id.name
            if weavng_wise_report == "Product Wise Report":
                product = rec.product_id.default_code

            # if rec.main_jobwork_id.sale_id.id == rec.mrp_work_order_id.sale_id.id:
            new_data.append({
                'order_no': rec.main_jobwork_id.reference,
                'date': rec.main_jobwork_id.issue_date.strftime('%d/%b/%y'),
                'due_date':  rec.main_jobwork_id.expected_received_date.strftime('%d/%b/%y'),
                'job_worker':  rec.main_jobwork_id.subcontractor_id.name,
                'sale_no':  rec.mrp_work_order_id.sale_id.order_no,
                'product':  rec.product_id.default_code,
                'size':  rec.product_id.product_template_variant_value_ids.name,
                'pcs':  rec.product_qty,
                'total_area':  rec.total_area,
                'rate':  rec.rate,
                'incentive':  rec.incentive
            })                
            total_pcs.append(rec.product_qty)
            total_area.append(rec.total_area)
            total_rate.append(rec.rate)
            total_incentive.append(rec.incentive)

        if not records:
            raise UserError("Record does not found")

        data = {
            'total_pcs': sum(total_pcs),
            'total_area': sum(total_area),
            'total_rate': sum(total_rate),
            'total_incentive': sum(total_incentive),
            'to_date': to_date,
            'from_date': from_date,
            'weavng_wise_report': weavng_wise_report,
            'division': division,
            'product': product,
            'new_data': new_data
        }
        return {
            'doc_ids': docids,
            'doc_model': 'main.jobwork',
            'docs': records,
            'data': data,
        }
