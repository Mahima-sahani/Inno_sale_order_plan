from datetime import datetime
from odoo import models, api, _
from odoo.exceptions import UserError, ValidationError, MissingError
from num2words import num2words
import logging

_logger = logging.getLogger(__name__)

class ReportMaterialLoom(models.AbstractModel):
    _name = 'report.innorug_manufacture.report_material_on_loom'

    @api.model
    def _get_report_values(self, docids, data=None):
        
        to_date = data.get('to_date')
        from_date = data.get('from_date')
        docids = data.get('docids')
        subcontractor_id = data.get('subcontractor_id')
        total_bal_area = []

        records = self.env['main.jobwork'].browse(docids).filtered(lambda rec: rec.state not in ['cancel'])
        product_tmpl_data = {}
        
        for job_work in records:
            subcontractor = job_work.subcontractor_id
            jobwork_line_ids = job_work.jobwork_line_ids
            total_area_sum = sum([qty.total_area for qty in jobwork_line_ids])
            total_receive_sum = sum([qty.total_area/qty.product_qty*qty.received_qty for qty in jobwork_line_ids])
            balance_area = total_area_sum-total_receive_sum
            total_bal_area.append(balance_area)
            order_no = job_work.reference
            
            jobwork_components_lines = job_work.main_jobwork_components_lines 
            for line in jobwork_components_lines:
                groups = set(line.product_id.product_tmpl_id.mapped('raw_material_group'))
                for group in groups:
                    product_lines = jobwork_components_lines.filtered(lambda rec: rec.product_id.product_tmpl_id.raw_material_group == group)
                    qty = round(sum([line.alloted_quantity / total_area_sum * total_receive_sum - line.quantity_released  if total_area_sum > 0 else 0.0 for line in product_lines]),3)
                    
                    if group not in product_tmpl_data:
                        product_tmpl_data[group] = {}
                    
                    if order_no not in product_tmpl_data[group]:
                        product_tmpl_data[group][order_no] = {'design': line.product_id.default_code,'order_no':order_no,'subcontractor': subcontractor.name, 'quantity': 0, 'balance_area': round(balance_area,3),'reference':job_work.reference}
                    
                    product_tmpl_data[group][order_no]['quantity'] += qty
        # Prepare data for the report
        summary_data = {}
        
        for group, orders in product_tmpl_data.items():
            for order_no, data in orders.items():
                partner_name = data['subcontractor']
                quantity = data['quantity']
                balance_area = data['balance_area']
                order_no = data['order_no']
                design = data['design']
                reference = data['reference']
                
                if order_no not in summary_data:
                    summary_data[order_no] = {'order_no':order_no, 'quantities': {}, 'balance_area': balance_area,'design':design,'reference':reference,'subcontractor_id': partner_name}
                
                summary_data[order_no]['quantities'][group] = round(quantity, 3)
        
        groups = []        
        for key, value in summary_data.items():
            for group, val in value.get('quantities').items():
                if group not in groups:
                    if group != False:
                        groups.append(group)

        formatted_group = self.formated_groups(groups)

        report_data = {
            'to_date': to_date,
            'from_date': from_date,
            'subcontractor_id': subcontractor_id,
            'weaving_summary': summary_data,
            'groups': groups,
            'formatted_group': formatted_group,
            'total_bal_area': sum(total_bal_area)
        }

        if not records:
            raise UserError("Record does not found")
            
        return {
            'doc_ids': docids,
            'doc_model': 'stock.picking',
            'docs': records,
            'data': report_data,
        }

    def formated_groups(self, groups):
        formatted_groups = []

        for group in groups:
            if '_' in group:
                words = group.split('_')
                capitalized_words = [word.capitalize() for word in words]
                formatted_item = ' '.join(capitalized_words)
                formatted_groups.append(formatted_item)
            else:
                formatted_item = group.capitalize()
                formatted_groups.append(formatted_item)
            
        return formatted_groups
