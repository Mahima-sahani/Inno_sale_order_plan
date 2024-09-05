from odoo import fields, models, _, api
import logging
_logger = logging.getLogger(__name__)


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    finishing_material_line_id = fields.Many2one("finishing.materials")


    def connect_operation(self):
        for rec in self:
            rec.update_parent_id(rec.workorder_ids.__len__() - 1)
        for rec in self.workorder_ids.filtered(lambda wo: wo.name != 'Weaving'):
            rec._compute_product_wo_qty()
        return {
            'name': 'Connect Operation',
            'view_mode': 'form',
            'res_model': 'inno.update.parent.operation',
            'type': 'ir.actions.act_window',
            'target': 'new',
        }

    def complete_operation_weaving_only_weaving(self):
        if self.workorder_ids.__len__() == 1:
            barcodes = self.env['mrp.barcode'].sudo().search(
                [('mrp_id', '=', self.id), ('state', '=', '5_verified')])
            for rec in barcodes:
                rec.move_barcode_inventory()
                rec.write({'state': '8_done', 'next_process': False, })
