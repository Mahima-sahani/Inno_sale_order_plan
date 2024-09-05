from odoo import models, fields, _, api
from odoo.exceptions import UserError
class StockQuantPackage(models.Model):
    _inherit = 'stock.quant.package'

    # def get_barcode_domain(self):
    #     for rec in self:
    #         if rec.quant_ids.__len__() > 1:
    #             return [('id', 'in', False)]
    #         else:
    #             barcodes = self.env['mrp.barcode'].search([('product_id', '=', rec.quant_ids.product_id.id),
    #                                                               ('state', '=', '8_done'),
    #                                                               ('sale_id', '=', rec.picking_id.sale_id.id)])
    #             if barcodes:
    #                 return [('id', 'in', barcodes.ids)]
    #             else:
    #                 return [('id', '=', False)]

    picking_id = fields.Many2one(comodel_name='stock.picking', string='Transfer')
    sale_id = fields.Many2one(related='picking_id.sale_id')
    # barcode_ids = fields.Many2many(comodel_name='mrp.barcode', string='Barcodes to Pack', domain=get_barcode_domain)
    barcode_ids = fields.Many2many(comodel_name='mrp.barcode', string='Barcodes to Pack')
    inno_shipping_weight = fields.Float(string='Total Weight')
    pack_image = fields.Binary(string='Packing Image')
    state = fields.Selection([('draft', 'DRAFT'),('packing', 'PACKING'),('done', 'DONE')],default='draft', string="State")
    roll_no = fields.Integer("Roll No")
    inno_package_id = fields.Many2one("inno.packaging")
    remark = fields.Char(string='Remark')


    def action_view_inno_picking(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Package Transfer"),
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'res_id': self.picking_id.id
        }

    @api.onchange('barcode_ids')
    def onchange_barcodes(self):
        for rec in self:
            if rec.barcode_ids.__len__() > sum(rec.quant_ids.mapped('quantity')):
                raise UserError(_("You can't assign more barcodes then available quantity"))

    def action_print_labels(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Print Labels"),
            'view_mode': 'form',
            'res_model': 'inno.print.package.label',
            'target': 'new'
        }
