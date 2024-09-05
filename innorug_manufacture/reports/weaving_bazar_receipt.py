from odoo import models, api
import logging
from datetime import datetime
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ReportWeavingBazar(models.AbstractModel):
    _name = 'report.innorug_manufacture.report_weaving_bazar_receipt'
    _description = 'Weaving Bazar Receipt'

    @api.model
    def _get_report_values(self, docids, data=None):

        docids = data.get('docids')
        records = self.env['main.baazar'].browse(docids)
        data = []
        weight_total = []
        pcs_total = []
        barcods = []
        for part in records.subcontractor_id:
            total_area = []
            rec = records.filtered(lambda baz: baz.subcontractor_id.id == part.id)
            baz_data = []
            for rec_no in rec:
                for prod in rec_no.baazar_lines_ids:
                    if prod.job_work_id.total_area != 0 and prod.job_work_id.product_qty != 0:
                        total_area.append(prod.job_work_id.total_area/prod.job_work_id.product_qty)
                    bar_data = rec_no.baazar_lines_ids.filtered(lambda bl: bl.product_id.id == prod.product_id.id)
                    sorted_bcode = sorted(bar_data.mapped('barcode'))
                    bcodes = []
                    init_data = ''
                    prev_data = ''
                    for scode in sorted_bcode:
                        code = scode.name
                        if not init_data:
                            init_data, prev_data = int(code), int(code)
                        elif prev_data+1 == int(code):
                            prev_data = int(code)
                        elif prev_data == init_data:
                            bcodes.append(f"{init_data}")
                            init_data, prev_data = int(code), int(code)
                        else:
                            bcodes.append(f"{init_data}-{prev_data}")
                            init_data, prev_data = int(code), int(code)
                    if prev_data == init_data:
                        bcodes.append(f"{init_data}")
                    else:
                        bcodes.append(f"{init_data}-{prev_data}")
                    if bcodes not in barcods:
                        baz_data.append({'design': prod.product_id.name, 'size': prod.product_id.inno_mrp_size_id.name,
                                        'quality': prod.product_id.product_tmpl_id.quality.name, 'pcs': bar_data.__len__(),
                                        'weight': round(sum([line.actual_weight for line in bar_data]), 3),
                                        'bcodes': ', '.join(bcodes), 'rec_no': rec_no.reference,
                                        'receive_date': rec_no.date.strftime('%d/%b/%Y'),
                                        'godown': rec_no.location_id.warehouse_id.name})
                    barcods.append(bcodes)

            total_weight = sum(entry['weight'] for entry in baz_data)
            weight_total.append(total_weight)
            total_pcs = sum(entry['pcs'] for entry in baz_data)
            pcs_total.append(total_pcs)
            total_pcs = sum(entry['pcs'] for entry in baz_data)
            data.append({'subcontractor': part.name, 'address': part.street,
                        'city': part.city, 'mobile': part.mobile, 'pan_no': part.pan_no, 'aadhar_no': part.aadhar_no,
                        'gst_no': part.vat, 'baz_data': baz_data, 'total_weight':total_weight,'total_pcs':total_pcs, 'total_area':sum(total_area)})
        if not records:
            raise UserError("Record does not found")


        return {
            'doc_ids': docids,
            'doc_model': 'main.baazar',
            'docs': records,
            'data': data,
        }
