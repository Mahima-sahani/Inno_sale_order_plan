from odoo import models, fields, api, _


class DyeingCancel(models.TransientModel):
    _name = 'dyeing.cancel'

    dyeing_order_id = fields.Many2one(comodel_name='dyeing.order', string='Dyeing Order')

    @api.model
    def default_get(self, fields_list):
        rec = super().default_get(fields_list)
        dyeing_order = self.env['dyeing.order'].browse(self._context.get('active_ids'))
        if dyeing_order:
            vals = [(0, 0, {'product_id': line.product_id.id, 'dyeing_intend_line_no': line.dyeing_intend_line_no,
                            'qty_available': (line.quantity - line.received_qty), 'po_no': line.po_no,})
                    for line in dyeing_order.sudo().dyeing_order_line_ids if (line.quantity - line.received_qty) > 0]
            rec.update({'dyeing_order_wiz_line': vals})
        return rec


class DyeingCancelLine(models.TransientModel):
    _name = 'dyeing.cancel.line'

    dyeing_order_id = fields.Many2one(comodel_name='dyeing.cancel')
    product_id = fields.Many2one(comodel_name='product.product', string='Product Name')
    qty_available = fields.Float(digts=(10, 4), string='Cancellation Availbale')
    quantity = fields.Float(digts=(10, 4), string='Cancel Quantity')
    dyeing_intend_line_no = fields.Many2one(comodel_name='dyeing.intend.line')
    po_no = fields.Char(string='PO Number')
