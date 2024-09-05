from datetime import datetime
from odoo import models, api,_
from odoo.exceptions import UserError, ValidationError, MissingError
from itertools import groupby
import logging

_logger = logging.getLogger(__name__)

class ReportPackagingPosition(models.AbstractModel):
    _name = 'report.inno_packaging.report_packaging_position'

    @api.model
    def _get_report_values(self, docids, data=None):

        docids = data.get('docids')
        to_date = data.get('to_date')
        from_date = data.get('from_date')
        records = self.env['inno.packaging'].browse(docids)
        total_bale_sum = []
        total_pcs = []
        total_area = []
        total_weight = []
        total_net_weight = []

        data = []
        for packaging in records:
            buyer_code = packaging.buyer_id.job_worker_code
            job_worker_id = packaging.job_worker_id
            packaging_no = packaging.name
            for invoice_group in packaging.stock_quant_lines.invoice_group_id:
                inv_grp = invoice_group.name
                line_data = packaging.stock_quant_lines.filtered(lambda rec: rec.invoice_group_id.id == invoice_group.id)
                # area_sq_yard = sum([area.area_sq_yard for area in line_data])
                area_sq_ft = sum([area.area_sq_feet for area in line_data])
                gross_weight = sum([gross_weight.gross_weight for gross_weight in line_data])
                net_weight = sum([net_weight.net_weight for net_weight in line_data])
                bale_no = sorted(line_data.mapped('roll_no'))
                
                bale_ranges = self.format_ranges(bale_no)
                bale_range_str = ', '.join(bale_ranges)
                
                bale_count = len(set(bale_no))
                pcs = len(line_data)

                total_bale_sum.append(bale_count)
                total_pcs.append(pcs)
                total_area.append(area_sq_ft)
                total_weight.append(gross_weight)
                total_net_weight.append(net_weight)
                
                data.append({
                    'buyer_code': buyer_code,
                    'quality': inv_grp,
                    'job_worker': job_worker_id.name,
                    'bale_no': bale_range_str,
                    'total_bale': bale_count,
                    'pcs': pcs,
                    'area_sq_yard': area_sq_ft,
                    'gross_weight': gross_weight,
                    'net_weight': net_weight,
                    'packaging_no': packaging_no
                })
        
        if not records:
            raise UserError("Record does not found") 

        report_data = {
            'doc_ids': docids,
            'doc_model': 'inno.packaging',
            'docs': records,
            'data': data,
            'total_bale_sum': sum(total_bale_sum),
            'total_pcs': sum(total_pcs),
            'total_area': sum(total_area),
            'total_weight': sum(total_weight),
            'total_net_weight': sum(total_net_weight),
            'to_date': to_date,
            'from_date': from_date,
        }
        return report_data
    
    def format_ranges(self, numbers):
        if not numbers:
            return []

        ranges = []
        start = end = numbers[0]

        for num in numbers[1:]:
            if num == end + 1:
                end = num
            elif num == end:  # Handle consecutive duplicates
                continue
            else:
                if start == end:
                    ranges.append(f"{start}")
                else:
                    ranges.append(f"{start}-{end}")
                start = end = num

        # Append the last range
        if start == end:
            ranges.append(f"{start}")
        else:
            ranges.append(f"{start}-{end}")

        return ranges
