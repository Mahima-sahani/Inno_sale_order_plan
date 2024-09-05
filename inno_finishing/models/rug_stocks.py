from odoo import fields, models, api, _
from odoo.exceptions import UserError
import base64


class RugStocks(models.Model):
    _inherit = 'stock.location'

    finishing_work_id = fields.Many2one(comodel_name="finishing.work.order", string="Finishing")

    def action_view_mrp_stock_lpcation(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Barcodes"),
            'view_mode': 'tree,form',
            'res_model': 'mrp.barcode',
            "target": "current",
            'context':{'group_by': 'product_id'},
            "domain": [('location_id', '=', self.id)]
        }


class RugStocksFinishing(models.Model):
    _inherit = 'stock.picking'

    finishing_work_id = fields.Many2one(comodel_name="finishing.work.order", string="Finishing")
    extra_material_type = fields.Selection([('amended', 'Amended'),
                               ('return', 'Return')],)

    def button_validate(self):
        for rec in self:
            res = super().button_validate()
            if rec.finishing_work_id and res == True:
                for material in rec.move_ids:
                    lines =rec.sudo().finishing_work_id.material_lines.filtered(
                        lambda mat: mat.product_id.id == material.product_id.id)
                    lines.qty_released += material.quantity_done
                    if self.extra_material_type == 'amended':
                        lines.qty_amended += material.quantity_done
                    elif self.extra_material_type == 'return':
                        lines.qty_return += material.quantity_done
            return res
