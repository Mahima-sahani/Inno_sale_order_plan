from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AddPercentBom(models.TransientModel):
    _name = 'bom.percent.wizard'

    product_id = fields.Many2one('product.product', string="Product")
    remaining_percent= fields.Float("Remaining")
    bom_id = fields.Many2one("mrp.bom")
    quality = fields.Float("Quality")
    bom_percent_lines = fields.One2many("bom.percent.wizard.lines", 'bom_percent_id', string="Sku Details")
    product_tmpl_id = fields.Many2one('product.template', string="Product")

    @api.model
    def default_get(self, fields_list):
        rec = super().default_get(fields_list)
        mrp_bom = self.env['mrp.bom'].browse(self._context.get('active_id'))
        if mrp_bom.bom_line_ids:
            vals = [(0, 0, {'material_id': line.product_id.id, 'qty': 0,}) for line in mrp_bom.bom_line_ids]
            rec.update({'bom_id': mrp_bom.id, 'remaining_percent' : 100, 'bom_percent_lines': vals, 'product_id' : mrp_bom.product_id.id,'product_tmpl_id' : mrp_bom.product_tmpl_id.id if not mrp_bom.product_id.id else False,  'quality' : mrp_bom.product_tmpl_id.quality.weight * mrp_bom.product_id.mrp_area if mrp_bom.product_id else mrp_bom.product_tmpl_id.quality.weight})
        return rec

    @api.onchange('bom_percent_lines')
    def onchange_based_percentage(self):
        self.remaining_percent = (100 - round(sum(self.bom_percent_lines.mapped('percent')), 3))
        if self.remaining_percent < 0:
            raise UserError(_("Percentage should not exceed 100"))

    def confirm(self):
        if self.bom_percent_lines and self.remaining_percent == 0:
            self.bom_id.bom_line_ids = False
            operation_id = self.bom_id.operation_ids.filtered(lambda op: 'Weaving' in op.mapped('name'))
            self.bom_id.write({
                'bom_line_ids': [
                    (0, 0, {'product_id': rec.material_id.id,
                            'product_qty': rec.qty,
                            'percentage' : rec.percent,
                            'operation_id': operation_id.id,
                            })  for rec in self.bom_percent_lines]})
            if not self.product_id:
                inno_rech_id = self.env['inno.research'].search([('name', '=', self.product_tmpl_id.name)], limit=1)
                rech_id = self.env['inno.research'].search([('design', '=', self.product_tmpl_id.name)], limit=1)
                if inno_rech_id or rech_id:
                    self.bom_id.bom_line_ids.write({"research_id" : inno_rech_id.id if inno_rech_id else rech_id.id})
            self.bom_id.message_post(body="<b>Percentage added</b>")
            self._cr.commit()
        else:
            raise UserError(_("Remaining percentage should be zero"))


class AddPercentBomline(models.TransientModel):
    _name = 'bom.percent.wizard.lines'

    bom_percent_id = fields.Many2one('bom.percent.wizard')
    material_id = fields.Many2one('product.product', string="Product")
    qty = fields.Float( string="Quantity")
    uom_id = fields.Many2one(related="material_id.uom_id")
    percent = fields.Float(digits=(10, 4), string="Percentage")
    other = fields.Boolean("Other")

    @api.onchange('percent')
    def onchange_percentage(self):
        self.qty = (self.bom_percent_id.quality / 100) * self.percent