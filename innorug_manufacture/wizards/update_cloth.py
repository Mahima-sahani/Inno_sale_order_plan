from odoo import models, fields, api, _
from odoo.exceptions import UserError


class UpdateCloth(models.TransientModel):
    _name = 'inno.update.cloth'
    _description = 'update cloth'

    move_id = fields.Many2one(comodel_name='stock.move', string='Stock Move')
    demand_qty = fields.Float(digits=(5, 3), related='move_id.product_uom_qty')
    update_cloth_line_ids = fields.One2many(comodel_name='inno.update.cloth.line', inverse_name='update_cloth_id',
                                            string='Available Quantity')
    picking_id = fields.Many2one(comodel_name='stock.picking', string='Delivery Order')

    @api.onchange('update_cloth_line_ids')
    def onchange_quantity(self):
        if sum(self.update_cloth_line_ids.mapped('quantity')) > self.demand_qty:
            raise UserError(_("Quantity should not be greater than the demand quantity"))

    def confirm_update(self):
        if sum(self.update_cloth_line_ids.mapped('quantity')) > self.demand_qty:
            raise UserError(_("Quantity should not be greater than the demand quantity"))
        dest_location = self.env['stock.location'].search([('usage', '=', 'supplier')], limit=1).id
        vals = []
        for line in self.update_cloth_line_ids.filtered(lambda cl: cl.quantity > 0):
            vals.append((0, 0,
                         {'name': f"Transfer : {self.picking_id.sudo().main_jobwork_id.reference}",
                          'product_id': line.product_id.id, 'product_uom_qty': line.quantity,
                          'product_uom': line.product_id.uom_id.id, 'location_id': self.picking_id.location_id.id,
                          'location_dest_id': dest_location}))
            component_line = self.picking_id.sudo().main_jobwork_id.main_jobwork_components_lines.filtered(
                lambda mjc: line.product_id.id in mjc.product_id.ids)
            if not component_line:
                self.picking_id.sudo().main_jobwork_id.write(
                    {'main_jobwork_components_lines': [(0, 0, {'product_id': line.product_id.id,
                                                               'alloted_quantity': line.quantity,
                                                               'product_uom': line.product_id.uom_id.id})]})
            else:
                component_line.alloted_quantity += line.quantity
            self.picking_id.sudo().main_jobwork_id.main_jobwork_components_lines.filtered(
                lambda mat: mat.product_id.id == self.move_id.product_id.id).alloted_quantity -= line.quantity
            self.move_id.product_uom_qty -= line.quantity
        self.picking_id.sudo().write({'move_ids': vals})
        if self.move_id.product_uom_qty == 0.00:
            self.picking_id.sudo().main_jobwork_id.main_jobwork_components_lines.filtered(
                lambda mat: mat.product_id.id == self.move_id.product_id.id).unlink()
            # self.sudo().move_id.unlink()


class UpdateClothLine(models.TransientModel):
    _name = 'inno.update.cloth.line'
    _description = 'new product'

    update_cloth_id = fields.Many2one(comodel_name='inno.update.cloth')
    product_id = fields.Many2one(comodel_name='product.product', string='Product',
                                 domain=[('is_raw_material', '=', True)])
    quantity = fields.Float(digits=(5, 3))
