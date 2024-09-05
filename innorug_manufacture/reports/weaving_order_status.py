from odoo import models, api
import datetime


class ReportJobWorkReIssue(models.AbstractModel):
    _name = 'report.innorug_manufacture.report_weaving_order_status_summary'
    _description = 'Weaving Order Status Summary'

    @api.model
    def _get_report_values(self, docids, data=None):
        records = self.env['main.jobwork'].sudo().browse(self._context.get('active_ids'))
        company = self.env['res.company'].search([], limit=1)
        prepared_data = dict()
        add_details = False
        for rec in records.subcontractor_id.ids:
            for job_work in records.filtered(lambda dat: dat.subcontractor_id.id == rec):
                summary_data = dict()
                for design in job_work.jobwork_line_ids.product_id.product_tmpl_id:
                    total_ord_pcs, tota_can_pcs, total_rec_pcs, total_bal_pcs = 0, 0, 0, 0
                    bal_area = 0
                    add_details = True
                    design_data = job_work.jobwork_line_ids.filtered(lambda jl: jl.product_id.product_tmpl_id.id == design.id)
                    for po in design_data.barcodes.sale_id:
                        po_wise_data = design_data.barcodes.filtered(lambda bcode: bcode.sale_id.id == po.id)
                        for size in set(po_wise_data.mapped('size')):
                            order_pcs = po_wise_data.filtered(lambda pd: pd.size == size).__len__()
                            can_pcs = po_wise_data.filtered(lambda pd: pd.id in job_work.cancelled_barcodes.ids and pd.size == size).__len__()
                            rec_pcs = po_wise_data.filtered(lambda pd: pd.size == size and pd.id not in job_work.cancelled_barcodes.ids and pd.state not in ['1_draft', '2_allotment', '3_allocated']).__len__()
                            bal_pcs = order_pcs-rec_pcs-can_pcs
                            if add_details:
                                summary_data[f"{size}+{po.name}"] = \
                                    {'order_no': job_work.reference, 'date': job_work.issue_date.strftime('%d/%b/%m'),
                                     'due_date': job_work.expected_received_date.strftime('%d/%b/%m'), 'design': design.name,
                                     'quality': design.quality.name, 'po': po.order_no, 'size': size,
                                     'color': '', 'ordered_pcs': order_pcs, 'can_pcs': can_pcs,
                                     'rec_pcs': rec_pcs, 'bal_pcs': bal_pcs}
                                add_details = False
                            else:
                                summary_data[f"{size}+{po.name}"] = \
                                    {'size': size, 'color': '', 'ordered_pcs': order_pcs, 'can_pcs': can_pcs,
                                     'rec_pcs': rec_pcs, 'bal_pcs': bal_pcs}
                            total_ord_pcs += order_pcs
                            tota_can_pcs += can_pcs
                            total_rec_pcs += rec_pcs
                            total_bal_pcs += bal_pcs
                prepared_data[rec] = {'name': job_work.subcontractor_id.name, 'ord_total': total_ord_pcs,
                                      'mobile': job_work.subcontractor_id.mobile, 'can_total': tota_can_pcs,
                                      'rec_total': total_rec_pcs, 'bal_total': total_bal_pcs, 'bal_area': bal_area,
                                      'data': [data for data in summary_data.values()]}
        data['records'] = [data for data in prepared_data.values()]
        return {'doc_ids': docids, 'doc_model': 'main.jobwork', 'data': data, 'company': company}
