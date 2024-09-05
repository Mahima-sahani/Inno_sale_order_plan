from odoo import models, fields, api, _
from odoo.exceptions import UserError


class InnoStockTransfer(models.TransientModel):
    _name = 'inno.stock.transfer'

    from_location = fields.Many2one(comodel_name='stock.location', string='From', domain=[('usage', '=', 'internal')],
                                    default=lambda self: self.env.user.material_location_id.id)
    to_location = fields.Many2one(comodel_name='stock.location', string='To', domain=[('usage', '=', 'internal')])
    stock_transfer_ids = fields.One2many(comodel_name='inno.stock.transfer.line', inverse_name='stock_transfer_id')

    def confirm_transfer(self):
        operation_type = self.from_location.warehouse_id.int_type_id
        job_stock_move = [(0, 0, {'name': f"Internal Transfer by {self.env.user.name}",
                                  'product_id': rec.product_id.id, 'product_uom_qty': rec.quantity,
                                  'product_uom': rec.product_id.uom_id.id, 'location_id': self.from_location.id,
                                  'location_dest_id': self.to_location.id, 'quantity_done': rec.quantity})
                          for rec in self.stock_transfer_ids if rec.quantity > 0 and rec.product_id]
        if not job_stock_move:
            raise UserError(_("Please check product line"))
        vals = {
            'name': operation_type.sequence_id.next_by_id(),
            'partner_id': self.env.user.commercial_partner_id.id,
            'picking_type_id': operation_type.id,
            'location_id': self.from_location.id,
            'location_dest_id': self.to_location.id,
            'move_ids': job_stock_move,
            'state': 'draft',
            'origin': f"Stock Transfer by {self.env.user.name}"
        }
        picking = self.env['stock.picking'].sudo().create(vals)
        picking.button_validate()


class InnoStockTransferLine(models.TransientModel):
    _name = 'inno.stock.transfer.line'

    stock_transfer_id = fields.Many2one(comodel_name='inno.stock.transfer')
    product_id = fields.Many2one(comodel_name ='product.product', string='Product')
    in_hand = fields.Float(compute='get_onhand_qty')
    quantity = fields.Float(digits=(10, 3), string='Quantity')
    uom_id = fields.Many2one(related='product_id.uom_id')

    @api.depends('product_id')
    def get_onhand_qty(self):
        for rec in self:
            materials = self.env['stock.quant'].sudo().search([('location_id','=', rec.env.user.material_location_id.id),('product_id','=', rec.product_id.id)])
            rec.write({'in_hand': 0.00})
            if materials:
                qty = sum([mat.quantity for mat in materials])
                rec.write({'in_hand': qty})



