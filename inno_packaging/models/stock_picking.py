from odoo import models, fields, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    po_number = fields.Char(string='PO Number', related='sale_id.order_no')
    inno_package_ids = fields.Many2many(comodel_name='stock.quant.package', string='Product Packages', copy=False)
    package_count = fields.Integer(compute='_compute_inno_packages')

    def _compute_inno_packages(self):
        for rec in self:
            rec.package_count = rec.inno_package_ids.__len__() or 0

    def action_put_in_pack(self):
        for rec in self:
            if rec.inno_package_ids:
                raise UserError(_("Products are already in Packages."))
            if rec.sale_id and rec.picking_type_id.code == 'outgoing':
                rec.create_packages()
            else:
                super().action_put_in_pack()

    def create_packages(self):
        package_vals = self.prepare_package_vals()
        packages = self.env['stock.quant.package'].create(package_vals)
        self.inno_package_ids = packages

    def prepare_package_vals(self):
        package_vals = []
        for move_line in self.move_line_ids:
            if not move_line.qty_done:
                raise UserError(_('Please Insert Done Qty(s) before putting the products in pack.'))
            if move_line.package_weight <= 0.0:
                raise UserError(_('Please Insert weight of the product.'))
            if move_line.product_id.packaging_ids:
                to_pack = move_line.qty_done
                qty_in_one_pack = move_line.product_id.packaging_ids.qty
                while to_pack:
                    package_vals.append({
                        'pack_image': move_line.product_id.image_1920,
                        'package_use': 'disposable', 'pack_date': fields.datetime.now(),
                        'location_id': move_line.location_id.id,
                        'picking_id': self.id,
                        'inno_shipping_weight': move_line.package_weight * to_pack if to_pack < qty_in_one_pack else qty_in_one_pack,
                        'quant_ids': [(0, 0, {'product_id': move_line.product_id.id,
                                              'quantity': to_pack if to_pack < qty_in_one_pack else qty_in_one_pack,
                                              'location_id': move_line.location_id.id})]
                    })
                    to_pack -= to_pack if to_pack < qty_in_one_pack else qty_in_one_pack
            else:
                package_vals.extend([{
                    'pack_image': move_line.product_id.image_1920,
                    'package_use': 'disposable',
                    'picking_id': self.id,
                    'pack_date': fields.datetime.now(),
                    'location_id': move_line.location_id.id,
                    'inno_shipping_weight': move_line.package_weight,
                    'quant_ids': [(0, 0, {'product_id': move_line.product_id.id, 'quantity': 1,
                                          'location_id': move_line.location_id.id})]
                } for qty in range(int(move_line.qty_done))])
        return package_vals

    def action_open_inno_pickings(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Product Packages"),
            'view_mode': 'kanban,tree,form',
            'res_model': 'stock.quant.package',
            'domain': [('id', 'in', self.inno_package_ids.ids)]
        }

    def button_validate(self):
        res = super().button_validate()
        for rec in self:
            if res == True and rec.sale_id and rec.inno_package_ids:
                rec.inno_package_ids.write({'location_id': rec.location_dest_id.id})
                rec.inno_package_ids.barcode_ids.write({'state': '10_done'})
        return res

