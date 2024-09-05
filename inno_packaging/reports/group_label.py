import datetime
from odoo import models, api

class ReportCargo(models.AbstractModel):
    _name = 'report.inno_packaging.report_print_group_label'
    _description = 'Will prepare the data for group label'

    @api.model
    def _get_report_values(self, docids, data=None):
        record = self.env['inno.packaging.invoice'].browse(data.get('doc_ids'))
        report_type = data.get('report_type')
        data = []
        tmp_data = []
        seen_roll_no = set()
        current_index = 1
        
        sorted_lines = record.pack_invoice_line_ids.sorted(lambda rec: rec.roll_no)
        
        for rec in sorted_lines:
            roll_no = rec.roll_no
            
            if roll_no not in seen_roll_no:
                if len(tmp_data) == 2:
                    data.append(tmp_data)
                    tmp_data = []
                
                tmp_data.append({
                    'group_no': roll_no,
                    'inv_group': rec.invoice_group.name,
                    'roll_no': current_index
                })
                
                seen_roll_no.add(roll_no)
                current_index += 1
            
        if tmp_data:
            data.append(tmp_data)
        
        return {
            'doc_ids': docids,
            'doc_model': 'inno.packaging',
            'docs': record,
            'data': data,
            'report_type': report_type
        }
