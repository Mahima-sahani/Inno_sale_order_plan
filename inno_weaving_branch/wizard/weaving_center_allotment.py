from odoo import models, fields, api, _
from odoo.exceptions import UserError


class WeavingCenterAllotment(models.TransientModel):
    _name = 'weaving.center.allotment'
    _description = 'Used for Allocating job work from Branch to subcontractor'

    issue_date = fields.Date(string='Issue Date')
    expected_date = fields.Date("Expected Date")
    allotment_line_ids = fields.One2many(comodel_name="weaving.center.allotment.line", inverse_name="wc_allotment_id")
    subcontractor_id = fields.Many2one(comodel_name='res.partner', string='Subcontractor')
    parent_jobwork_id = fields.Many2one(comodel_name='main.jobwork')
    branch_id = fields.Many2one(comodel_name='weaving.branch')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        allotments = self.env['jobwork.allotment'].browse(self._context.get('active_ids'))
        if allotments.jobwork_id.ids.__len__() > 1:
            raise UserError(_("You Can't allot allotments related to different job work."))
        if not allotments.jobwork_id.barcode_released:
            raise UserError(_(f"Please Confirm and Release the barcodes for Job Work {allotments.jobwork_id.reference}"))
        vals = [(0, 0, {'product_id': rec.product_id.id, 'product_qty': rec.remaining_product_qty,
                        'allotment_id': rec.id, 'work_order_id': rec.work_order_id.id})
                for rec in allotments]
        res.update({'allotment_line_ids': vals, 'parent_jobwork_id': allotments.jobwork_id.id,
                    'branch_id': allotments.branch_id.id})
        return res

    def do_confirm(self):
        jobwork_vals = self.create_job_work_record()
        job_work = False
        if jobwork_vals:
            job_work = self.env['main.jobwork'].sudo().create(jobwork_vals)
            for rec in self.allotment_line_ids:
                bcodes = self.update_barcode_data(job_work, rec)
                job = job_work.jobwork_line_ids.filtered(lambda jw: jw.allotment_id.id == rec.allotment_id.id)
                job.barcodes = bcodes.ids
        if job_work:
            job_work.create_sequence()
            return {'type': 'ir.actions.act_window', 'name': _("Main Job Work"), 'view_mode': 'form',
                'res_model': 'main.jobwork', 'res_id': job_work.id, "target": "current"}
        return False

    def update_barcode_data(self, job_work, rec):
        bcodes = rec.allotted_barcodes
        if bcodes.__len__() != rec.alloted_qty:
            raise UserError(_("Mismatch Barcodes and Allocated Quantity"))
        bcodes.write({'state': '3_allocated', 'main_job_work_id': job_work.id})
        return bcodes

    def create_job_work_record(self):
        job_vals = False
        config = self.env['inno.config'].sudo().search([], limit=1)
        if not config.allowed_fragments:
            raise UserError(_("Please ask your admin to set default allowed bazaar fragments(Chunks)."))
        job_line_vals = [(0, 0, {"mrp_work_order_id": rec.work_order_id.id, "product_qty": rec.alloted_qty,
                                 "total_area": rec.product_id.mrp_area * rec.alloted_qty, 'issue_date': self.issue_date,
                                 "product_id": rec.product_id.id, "allotment_id": rec.allotment_id.id,
                                 "area": rec.product_id.mrp_area,
                                 'uom_id': rec.product_id.sudo().get_rate_list_uom(rec.work_order_id.workcenter_id),
                                 # 'original_rate': rec.product_id.sudo().calculate_product_rate(rec.work_order_id.workcenter_id)
                                 'original_rate': self.parent_jobwork_id.jobwork_line_ids.filtered(
                    lambda jl: rec.product_id.id in jl.product_id.ids)[0].rate
                                 })
                         for rec in self.allotment_line_ids if rec.alloted_qty > 0]
        if job_line_vals:
            job_vals = {'work_order_ids': self.allotment_line_ids.work_order_id.ids,
                        'jobwork_line_ids': job_line_vals, 'subcontractor_id': self.subcontractor_id.id,
                        'operation_id': self.allotment_line_ids.work_order_id.workcenter_id.id,
                        "parent_job_work_id": self.parent_jobwork_id.id, 'branch_id': self.branch_id.id,
                        'issue_date': self.issue_date, 'expected_received_date': self.expected_date,
                        'allowed_chunks': config.allowed_fragments,
                        'barcode_released': True, 'division_id': self.parent_jobwork_id.division_id.id}
        return job_vals


class WeavingCenterAllotmentLine(models.TransientModel):
    _name = 'weaving.center.allotment.line'

    product_id = fields.Many2one("product.product", string="Product")
    product_qty = fields.Float(string="Quantity")
    alloted_qty = fields.Float(string="Allotted Qty")
    work_order_id = fields.Many2one(comodel_name="mrp.workorder")
    wc_allotment_id = fields.Many2one(comodel_name="weaving.center.allotment")
    allotment_id = fields.Many2one(comodel_name='jobwork.allotment')
    allotted_barcodes = fields.Many2many(comodel_name='mrp.barcode')

    @api.onchange('alloted_qty')
    def onchange_alloted_qty(self):
        for rec in self:
            rec.allotted_barcodes = False
            if rec.alloted_qty > rec.product_qty:
                raise UserError(_("You Can't Allot more quantities than available to allot."))
            if rec.alloted_qty > 0:
                rec.write({'allotted_barcodes': [(4, line.id) for line in rec.allotment_id.barcodes.filtered(
                    lambda bcode: bcode.state == '2_allotment')[0: int(rec.alloted_qty)]]})
            else:
                return {'domain': {'allotted_barcodes': [('id', 'in', [])]}}

    @api.onchange('allotted_barcodes')
    def onchange_barcodes(self):
        for rec in self:
            if rec.allotted_barcodes.__len__() > rec.alloted_qty:
                raise UserError("You can't allot more barcodes than allotted Qty quantity.")