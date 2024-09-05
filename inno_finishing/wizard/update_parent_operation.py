from odoo import models, fields, api,_
from odoo.exceptions import UserError, ValidationError, MissingError


class UpdateParentOperation(models.TransientModel):
    _name = 'inno.update.parent.operation'

    next_operation = fields.Many2one('mrp.workorder')


    def confirm_update(self):
        productions = self.env['mrp.production'].browse(self._context.get('active_id'))
        if productions:
            barcodes = self.env['mrp.barcode'].sudo().search(
                [('mrp_id', '=', productions.id),('state', '=', '5_verified')]).filtered(lambda br: not br.next_process )
            if barcodes:
                barcodes.write({'next_process' : self.next_operation.id})
