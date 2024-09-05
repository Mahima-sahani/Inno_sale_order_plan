from odoo import fields, models, _,api
from datetime import datetime
from odoo.exceptions import UserError
import requests
import logging
_logger = logging.getLogger(__name__)


class SaleOrderPlanning(models.Model):
    _inherit = "inno.sale.order.planning"

    def update_mo_bom(self):
        for rec in self.env['mrp.production'].search([]).move_raw_ids:
            if not rec.bom_line_id:
                rec.product_uom_qty = rec.raw_material_production_id.bom_id.bom_line_ids.filtered(lambda
                                                                                                      bml: bml.product_id.id == rec.product_id.id).product_qty * rec.raw_material_production_id.product_uom_qty
            else:
                rec.product_uom_qty = rec.bom_line_id.product_qty * rec.raw_material_production_id.product_uom_qty


    # def create_product_planning_report(self):
    #     self.update_mrp_size()
    #     return super().create_product_planning_report()

    def update_mrp_size(self):
        products = self.sale_order_planning_lines.product_id.filtered(
            lambda pd: pd.shape_type in ['circle'] and not pd.is_mrp_update)
        for rec in products:
            if rec.inno_mrp_size_id:
                size = rec.inno_mrp_size_id.name
                size = size.replace("RD", '')
                lines = self.env['inno.size'].search([('name', '=', size.strip())])
                if lines:
                    rec.write({'inno_mrp_size_id': lines.id, 'is_mrp_update': True})
                else:
                    raise UserError(_(f'{size} not found'))
        products = self.sale_order_planning_lines.product_id.filtered(
            lambda pd: pd.shape_type in ['circle'] and pd.is_mrp_update)
        for rec in products:
            bom=rec.bom_ids.filtered(lambda bm: not bm.product_id)
            bom.re_sync_materials()
            bom.re_sync_operations()

    def resync_bom(self):
        self.update_mrp_size()
        self.update_mo_bom()
        return super().resync_bom()




