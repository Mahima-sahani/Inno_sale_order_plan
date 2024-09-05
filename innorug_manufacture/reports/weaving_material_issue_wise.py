from collections import defaultdict
from datetime import datetime
import calendar
from odoo.exceptions import UserError
from odoo import models, api
import logging

_logger = logging.getLogger(__name__)

class ReportWeavingIssueSummary(models.AbstractModel):
    _name = 'report.innorug_manufacture.report_weaving_material_issue_wise'

    @api.model
    def _get_report_values(self, docids, data=None):
        to_date = data.get('to_date')
        from_date = data.get('from_date')
        docids = data.get('docids')
        subcontractor_id = data.get('subcontractor_id')

        if data.get('report_type') == "weaving_material_issue": 
            report_type = "Material Issue For Weaving Summary(Issue No Wise)" 
        else:
            report_type =  "Material Receive For Weaving Summary(Receive No Wise)"
        
        type_report = "Party Wise Summary" if data.get('subcontractor_id') else "Date Wise Summary" if data.get('from_date') else "General Summary"
        
        records = (self.env['stock.picking'].browse(docids).
                   filtered(lambda rec: rec.picking_type_code == 'outgoing' and rec.state == 'done' and rec.main_jobwork_id)) if \
            (data.get('report_type') == "weaving_material_issue") else \
            (self.env['stock.picking'].browse(docids).
             filtered(lambda rec: rec.picking_type_code == 'incoming' and rec.state == 'done'))
        sorter_record = records.sorted(lambda rec: rec.date_done)

        issue_no_wise_summary = {}

        for picking in sorter_record:
            
            date = picking.date_done.strftime("%d/%b/%y")
            issue_no = picking.name
            main_jobwork_id = picking.main_jobwork_id.reference
            move_lines = picking.filtered(lambda pick: pick.name == issue_no).move_line_ids
            groups = set(move_lines.product_id.product_tmpl_id.mapped('raw_material_group'))

            for group in groups:
                product_lines = move_lines.filtered(lambda rec: rec.product_id.product_tmpl_id.raw_material_group == group)
                done_qty = round(sum([rec.qty_done for rec in product_lines]), 3)
                if group not in issue_no_wise_summary:
                    issue_no_wise_summary[group] = {}
                if issue_no not in issue_no_wise_summary[group]:
                    issue_no_wise_summary[group][issue_no] = {'issue_no':issue_no,'quantity':0,'partner':picking.partner_id.name,'partner_id':picking.partner_id.id, 'date':date,'main_jobwork_id':main_jobwork_id}
                issue_no_wise_summary[group][issue_no]['quantity'] += done_qty
        # Prepare data for the report including month-wise summaries

        summary_data = {}
        for material, data in issue_no_wise_summary.items():
            for issue_no, data_dict in data.items():
                issue_no = data_dict['issue_no']
                partner = data_dict['partner']
                partner_id = data_dict['partner_id']
                date = data_dict['date']
                main_jobwork_id = data_dict['main_jobwork_id']
                quantity = round(data_dict['quantity'],3)
                if issue_no not in summary_data:
                    summary_data[issue_no] = {'issue_no': issue_no,'partner':partner,'partner_id':partner_id, 'quantities': {}, 'date':date,'main_jobwork_id':main_jobwork_id}
                summary_data[issue_no]['quantities'][material] = quantity
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
            'month_wise_summary': summary_data,
            'groups': groups,
            'formatted_group': formatted_group,
            'type_report_for_col' : data.get('report_type')
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
