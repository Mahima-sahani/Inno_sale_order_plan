from odoo import models, fields, api, _
from odoo.exceptions import UserError


class MrpWeaving(models.TransientModel):
    _inherit = 'mrp.weaving.wizards'

    branch_id = fields.Many2one("weaving.branch")
    allotment_type = fields.Selection(selection_add=[('branch', 'Branch')])

    def create_job_work_record(self):
        vals = super().create_job_work_record()
        if self.allotment_type == 'branch':
            if not self.branch_id.partner_id:
                raise UserError(_('Please configure partner in your branch.'))
            vals.update({'subcontractor_id': self.branch_id.partner_id.id, 'is_branch_subcontracting': True,
                         'weaving_center_name': self.branch_id.name})
        return vals

    def update_barcode_data(self, job_work, rec):
        if job_work:
            bcode = super().update_barcode_data(job_work, rec)
            if self.allotment_type == 'branch':
                if rec.alloted_qty > 0:
                    self.create_allotment_record(rec, bcode, job_work)
                bcode.write({'state': '2_allotment', 'main_job_work_id': False, 'branch_main_job_work_id': job_work.id,
                             'branch_id': self.branch_id.id})
            return bcode

    def create_allotment_record(self, rec, bcode, job_work):
        allotment = self.env['jobwork.allotment'].sudo().create({
            'product_qty': rec.alloted_qty,
            'work_order_id': rec.work_order_id.id,
            "branch_id": self.branch_id.id,
            "expected_received_date": self.expected_date,
            'jobwork_id': job_work.id
        })
        allotment.barcodes = bcode.ids
