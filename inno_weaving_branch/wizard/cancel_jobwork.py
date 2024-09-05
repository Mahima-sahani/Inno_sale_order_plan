from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CancelJobWork(models.TransientModel):
    _inherit = 'inno.cancel.job.work'

    branch_allocation = fields.Boolean()

    def do_confirm(self):
        if self.branch_allocation:
            cancel_barcodes =  False
            if self.full_cancellation:
                self.job_work_id.jobwork_line_ids.barcodes.write({'state': '2_allotment', 'main_job_work_id': False})
                for rec in self.job_work_id.jobwork_line_ids:
                    rec.return_quantity += rec.product_qty
                    rec.allotment_id.remaining_product_qty += rec.product_qty
                    rec.barcodes = False
                if self.penalty > 0.0:
                    self.env['inno.incentive.penalty'].create({
                        'partner_id': self.job_work_id.subcontractor_id.id,
                        'remark': f"Cancelled the job work {self.job_work_id.reference}",
                        'record_date': fields.Datetime.now(),
                        'amount': self.penalty,
                        'type': 'cancel'
                    })
                self.job_work_id.state = 'cancel'
                cancel_barcodes = self.job_work_id.jobwork_line_ids.barcodes
                self.job_work_id.write({'cancelled_barcodes': [(4, bcode.id) for bcode in cancel_barcodes]})
                # barcodes.write({'main_job_work_id'
            else:
                for rec in self.barcode_ids:
                    line=self.job_work_id.jobwork_line_ids.filtered(lambda jw: rec.id in jw.barcodes.ids)
                    for re in line:
                        re.return_quantity -= 1
                        re.allotment_id.remaining_product_qty +=1
                cancel_barcodes = self.barcode_ids
                self.job_work_id.write({'cancelled_barcodes': [(4, bcode.id) for bcode in self.barcode_ids]})
                self.add_barcode_penalty()
            for rec in cancel_barcodes:
                rec.write({'current_process': rec.mrp_id.workorder_ids.filtered(lambda wr: wr.name == 'Weaving').id, 'main_job_work_id': False})
            for rec in self.job_work_id.jobwork_line_ids:
                rec.allotment_id._compute_remaining_qty()
        else:
            return super().do_confirm()

    def add_barcode_penalty(self):
        if self.branch_allocation:
            self.barcode_ids.write({'state': '2_allotment', 'main_job_work_id': False, 'current_process': False,
                                    'pen_inc_ids':
                                        [(0, 0, {'type': 'cancel', 'record_date': fields.Datetime.now(),
                                                 'amount': self.penalty, 'remark': "Cancelled the Job",
                                                 'rec_id': self.job_work_id.id,
                                                 'workcenter_id': self.barcode_ids[0].current_process.id,
                                                 'model_id': self.env.ref('innorug_manufacture.model_main_jobwork').id})
                                         ]})
        else:
            super().add_barcode_penalty()
