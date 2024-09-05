from odoo import models


class InnoAmendQuantity(models.TransientModel):
    _inherit = 'inno.amend.return'

    def button_confirm(self):
        pick = self.transfer_stock_to_subcontracter()
        if self._context.get('branch_amendment'):
            pick.main_jobwork_id = self.job_order_id.parent_job_work_id.id
        if self._context.get('process') == 'amend':
            for rec in self.amend_return_ids:
                rec.component_line_id.amended_quantity += rec.quantity
                if self._context.get('branch_amendment'):
                    cmp_line = self.job_order_id.parent_job_work_id.component_line_id.filtered(
                        lambda cl: cl.product_id.id == rec.product_id.id)
                    cmp_line.amended_quantity += rec.quantity
        elif self._context.get('process') == 'return':
            for rec in self.amend_return_ids:
                rec.component_line_id.returned_quantity += rec.quantity
                if self._context.get('branch_amendment'):
                    cmp_line = self.job_order_id.parent_job_work_id.component_line_id.filtered(
                        lambda cl: cl.product_id.id == rec.product_id.id)
                    cmp_line.returned_quantity += rec.quantity
