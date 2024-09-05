from odoo import models


class BaazaProductLines(models.Model):
    _inherit = "mrp.baazar.product.lines"

    def update_finished_qty(self):
        super().update_finished_qty()
        if self.main_jobwork_id.parent_job_work_id:
            self.main_jobwork_id.parent_job_work_id.jobwork_line_ids.filtered(
                lambda jw: jw.product_id.id == self.job_work_id.product_id.id and self.barcode.id in jw.barcodes.ids).received_qty += 1
