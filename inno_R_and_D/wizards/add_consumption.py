from odoo import models, fields, api, _
from odoo.exceptions import UserError

class AddConsumption(models.TransientModel):
    _name = 'inno.rnd.bom.consumption'
    _description = 'Used to Import Design'

    template_id = fields.Many2one(comodel_name='product.template', string='Product', domain=[('is_raw_material', '=', True)])
    attribute_id = fields.Many2one(comodel_name='product.attribute.value', string='Shade')
    quantity = fields.Float(string='Quantity', digits='Stock Weight')
    uom_id = fields.Many2one(comodel_name='uom.uom', string='Product UOM',
                             default=lambda self: self.env['uom.uom'].search([('name', '=', 'kg')], limit=1).id)
    percentage = fields.Float(string='Percentage', digits='Stock Weight')
    no_shade = fields.Boolean(string="No Shade?")

    @api.onchange('percentage')
    def onchange_percentage(self):
        for rec in self:
            active_id = self.env[self._context.get('active_model')].browse(self._context.get('active_id'))
            if rec.percentage > 100.00:
                raise UserError(_("Percentage Should not be greater than 0"))
            if rec.percentage < 0.00:
                raise UserError(_("Percentage Should not be less than 0"))
            if round(rec.percentage, 2) > round(100 - sum(active_id.rnd_bom_lines.mapped('percentage')), 2):
                raise UserError(_("You Can't allocate more than 100 percentage of the quality."))
            self.quantity = (active_id.quality_weight / 100) * rec.percentage

    @api.onchange('template_id')
    def onchange_product_id(self):
        active_id = self.env[self._context.get('active_model')].browse(self._context.get('active_id'))
        if self.template_id:
            self.attribute_id = False
            shades = self.template_id.attribute_line_ids.value_ids.ids
            self.no_shade = False if shades else True
            if self.no_shade and self.template_id.product_variant_ids.id in active_id.rnd_bom_lines.product_id.ids:
                raise UserError(_("This product is already Exist in the BOM"))
            return {'domain': {'attribute_id': [('id', 'in', shades)]}}

    @api.onchange('attribute_id')
    def onchange_attribute_id(self):
        active_id = self.env[self._context.get('active_model')].browse(self._context.get('active_id'))
        product = self.template_id.product_variant_ids.filtered(
            lambda pv: pv.product_template_attribute_value_ids.product_attribute_value_id.id == self.attribute_id.id)
        if product.id in active_id.rnd_bom_lines.product_id.ids:
            raise UserError(_("This product is already Exist in the BOM"))
        self.percentage = 100 - sum(active_id.rnd_bom_lines.mapped('percentage'))
        self.onchange_percentage()

    def add_raw_material(self):
        active_id = self.env[self._context.get('active_model')].browse(self._context.get('active_id'))
        operation_id = active_id.rnd_route_lines.filtered(lambda rl: rl.workcenter_id.is_weaving_workcenter)
        if self.no_shade:
            product = self.template_id.product_variant_ids.id
        else:
            product = self.template_id.product_variant_ids.filtered(
                lambda pv: pv.product_template_attribute_value_ids.product_attribute_value_id.id == self.attribute_id.id)
        if product.id in active_id.rnd_bom_lines.product_id.ids:
            raise UserError(_("This product is already Exist in the BOM"))
        self.env['mrp.bom.line'].create({'product_id': product.id, 'product_qty': self.quantity,
                                         'product_uom_id': self.uom_id.id, 'research_id': active_id.id,
                                         'bom_id': active_id.bom_id.id, 'percentage': self.percentage,
                                         'operation_id': operation_id.id if operation_id else False})
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': "Record Created Successfully",
            }
        }
