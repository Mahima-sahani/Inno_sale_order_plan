from odoo import fields, models, _, api
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    job_order_id = fields.Many2one("mrp.job.work", "Job Order")
    rug_work_order_id = fields.Many2one("mrp.workorder", " Rug Work Order")
    division_id = fields.Many2one(related="product_id.product_tmpl_id.division_id", store=True, string='Division')
    final_qty_done = fields.Float(string='Quantity Manufactured', copy=False)

    def get_job_order_id_job_work(self):
        if self.product_id:
            if not self.job_order_id:
                self.job_order_id = self.job_order_id.create({
                    "mrp_production_id": self.id,
                    "product_id": self.product_id,
                    'qty_production' : self.product_qty
                })
            else:
                if self.job_order_id.mrp_production_id:
                    if self.job_order_id.product_id != self.product_id:
                        self.job_order_id.product_id = self.product_id
                        self.job_order_id.qty_production = self.product_qty
                else:
                    self.job_order_id.mrp_production_id = self.id
        return self.view_job_order_action()

    def view_job_order_action(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Job Work"),
            'view_mode': 'list,form,kanban',
            'res_model': 'mrp.job.work',
            'domain': [('mrp_production_id','=',self.id)]
        }

    def action_view_mrp_job_work(self):
        for rec in self.move_raw_ids:
            _logger.info("~~~~~~2~~~~~~%r~~~~rec~~~~",rec.product_uom_qty )
        if self.product_id:
            if not self.job_order_id:
                self.job_order_id = self.job_order_id.create({
                    "mrp_production_id": self.id,
                    "product_id": self.product_id,
                    'qty_production' : self.product_qty
                })
            else:
                if self.job_order_id.mrp_production_id:
                    if self.job_order_id.product_id != self.product_id:
                        self.job_order_id.product_id = self.product_id
                        self.job_order_id.qty_production = self.product_qty
                else:
                    self.job_order_id.mrp_production_id = self.id
        return self.view_job_order_action()

    def action_view_mrp_job_quality_control(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Quality Control"),
            'view_mode': 'list,form',
            'res_model': 'mrp.quality.control',
            # 'context': {
            #     'search_default_order_logs': 1,
            # },
            'domain': [('production_id', '=', self.id)]
        }

    def action_confirm(self):
        """
        This method is inherited to allocate the serial numbers to the mrp
        """
        if self._context.get('no_confirm_mo'):
            return
        for rec in self:
            division = rec.product_id.product_tmpl_id.division_id
            if division:
                if not division.location_id:
                    raise UserError(_("Please ask your manager to set location in your division."))
                rec.location_src_id = division.location_id.id
                rec.location_dest_id = division.location_id.id
                product_tmpl = rec.product_id.product_tmpl_id
                barcodes = rec.env['mrp.barcode'].create(
                    [{'name': self.env['ir.sequence'].next_by_code('production_barcode_seq'), 'design': product_tmpl.name,
                      'product_id': rec.product_id.id, 'size': rec.product_id.inno_mrp_size_id.name, 'state': '1_draft', 'mrp_id': rec.id,
                      'company_id': rec.company_id.id, 'sale_id': rec.move_dest_ids.group_id.sale_id.id}
                     for count in range(int(rec.product_qty))])
                barcodes.generate_barcode()
                rec.workorder_ids._compute_product_wo_qty()
            record = super().action_confirm()
            if division:
                self.do_unreserve()
            return record

    @api.model_create_multi
    def create(self, vals_list):
        record = super().create(vals_list)
        for rec in record:
            rec.update_parent_id(rec.workorder_ids.__len__()-1)
        return record

    def update_parent_id(self, wo_length):
        if wo_length < 1:
            return
        else:
            self.workorder_ids[wo_length].parent_id = self.workorder_ids[wo_length-1].id
            self.update_parent_id(wo_length-1)

    def button_mark_done(self):
        if self.product_id.product_tmpl_id.division_id:
            ready_moves = self.move_finished_ids.filtered(lambda m: m.product_id == self.product_id and m.state not in ('done', 'cancel'))
            done_qty = sum(self.move_finished_ids.filtered(lambda m: m.product_id == self.product_id and m.state in ('done', 'cancel')).mapped('quantity_done'))
            qty_to_finish = self.qty_producing - done_qty
            if qty_to_finish > 0:
                new_move = ready_moves.copy()
                new_move.write({'product_uom_qty': qty_to_finish, 'quantity_done': qty_to_finish})
                new_move._action_done()
                ready_moves.write({'product_uom_qty': ready_moves.product_uom_qty - qty_to_finish})
            if qty_to_finish and qty_to_finish == sum(ready_moves.mapped('quantity_done')):
                self.state = 'done'
        else:
            return super().button_mark_done()

    def button_plan(self):
        res = super().button_plan()
        self.date_planned_start = fields.datetime.today()
        return res

    def resync_material_data(self):
        self.ensure_one()
        if self.state == ['done', 'cancel']:
            raise UserError(_("This operation can not be performed for done or cancelled orders."))
        for rec in self.move_raw_ids:
            rec.product_uom_qty = rec.bom_line_id.product_qty * self.product_qty

    # def fix_operation(self, production_id):
    #     production = self.browse(production_id)
    #     production.workorder_ids[-1].parent_id = production.workorder_ids[0]
    #     production.workorder_ids[1].parent_id = production.workorder_ids[-1]
    #     production.workorder_ids[1].allotted_qty = 0
    #     self.env['mrp.barcode'].search([('mrp_id', '=', production.id)]).write({'next_process': production.workorder_ids[-1]})
