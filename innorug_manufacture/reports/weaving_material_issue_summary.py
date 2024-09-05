from datetime import datetime
from odoo import models, api, _
from odoo.exceptions import UserError, ValidationError, MissingError
from num2words import num2words
import logging

_logger = logging.getLogger(__name__)

class ReportWeavingIssueSummary(models.AbstractModel):
    _name = 'report.innorug_manufacture.report_weaving_material_summary'

    @api.model
    def _get_report_values(self, docids, data=None):
        
        to_date = data.get('to_date')
        from_date = data.get('from_date')
        docids = data.get('docids')
        subcontractor_id = data.get('subcontractor_id')


        if data.get('report_type') == "weaving_material_issue": 
            report_type = "Material Issue For Weaving Summary" 
        else:
            report_type =  "Material Receive For Weaving Summary"
        
        type_report = "Party Wise Summary" if data.get('subcontractor_id') else "Date Wise Summary" if data.get('from_date') else "General Summary"
        
        # Fetch records based on the report type
        records = (self.env['stock.picking'].browse(docids).
                   filtered(lambda rec: rec.picking_type_code == 'outgoing' and rec.state == 'done' and rec.main_jobwork_id)) if \
            (data.get('report_type') == "weaving_material_issue") else \
            (self.env['stock.picking'].browse(docids).
             filtered(lambda rec: rec.picking_type_code == 'incoming' and rec.state == 'done'))
        
        product_tmpl_data = {}
        for picking in records:
            partner = picking.partner_id
            move_lines = picking.filtered(lambda pick: pick.partner_id.id == partner.id).move_line_ids
            groups = set(move_lines.product_id.product_tmpl_id.mapped('raw_material_group'))
            for group in groups:
                product_lines = move_lines.filtered(lambda rec: rec.product_id.product_tmpl_id.raw_material_group == group)
                done_qty = round(sum([rec.qty_done for rec in product_lines]), 3)
                if group not in product_tmpl_data:
                    product_tmpl_data[group] = {}
                if partner.id not in product_tmpl_data[group]:
                    product_tmpl_data[group][partner.id] = {'partner': partner.name, 'quantity': 0}
                product_tmpl_data[group][partner.id]['quantity'] += done_qty
        # Prepare data for the report
        summary_data = {}
        for group, partners in product_tmpl_data.items():
            for partner_id, data in partners.items():
                partner_name = data['partner']
                quantity = data['quantity']
                if partner_name not in summary_data:
                    summary_data[partner_name] = {'partner_id': partner_id, 'quantities': {}}
                summary_data[partner_name]['quantities'][group] = round(quantity,3)
        
        groups = []
        for key,value in summary_data.items():
            for group,val in value.get('quantities').items():
                if group not in groups:
                    if group != False:
                        groups.append(group)

        formatted_group = self.formated_groups(groups)

        report_data = {
            'report_type': report_type,
            'type_report': type_report,
            'to_date': to_date,
            'from_date': from_date,
            'subcontractor_id': subcontractor_id,
            'weaving_summary': summary_data,
            'groups':groups,
            'formatted_group': formatted_group
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
