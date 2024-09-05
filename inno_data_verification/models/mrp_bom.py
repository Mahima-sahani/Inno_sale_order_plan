from odoo import models, fields, _
from odoo.exceptions import UserError
import base64


class MrpBom(models.Model):
    _inherit = 'mrp.bom'

    def re_sync_materials(self):
        boms = self.product_tmpl_id.bom_ids.filtered(lambda bom: bom.id != self.id)
        design_components = self.bom_line_ids
        for bom in boms:
            sku_id = bom.product_id
            operation_id = bom.operation_ids.filtered(lambda op: 'Weaving' in op.mapped('name'))
            bom.bom_line_ids.filtered(lambda bl: bl.product_id.id not in design_components.product_id.ids).unlink()
            order_lines = []
            for line in design_components:
                sku_line = bom.bom_line_ids.filtered(lambda bl: bl.product_id.id == line.product_id.id)
                if sku_line:
                    sku_line.product_qty = line.product_qty * sku_id.mrp_area
                else:
                    line_data = (0, 0, {
                        "product_id": line.product_id.id,
                        'product_qty': float(line.product_qty * sku_id.mrp_area),
                        'operation_id': operation_id.id
                    })
                    order_lines.append(line_data)
            bom.write({'bom_line_ids': order_lines
                       })
        self.message_post(body="<b>Updated Materials</b>")

    def re_sync_operations(self):
        boms = self.product_tmpl_id.bom_ids.filtered(lambda bom: bom.id != self.id)
        design_operations = self.operation_ids
        for bom in boms:
            bom.operation_ids.filtered(lambda op: op.workcenter_id.id not in design_operations.workcenter_id.ids).unlink()
            for operation in design_operations:
                existing_operation = bom.operation_ids.filtered(lambda op: op.workcenter_id.id == operation.workcenter_id.id)
                if existing_operation:
                    existing_operation.write({'sequence': operation.sequence})
                else:
                    bom.write({'operation_ids': [(0, 0, {'name': operation.name, 'sequence': operation.sequence,
                                                         'workcenter_id': operation.workcenter_id.id})]})
        self.message_post(body="<b>Updated Operation</b>")

