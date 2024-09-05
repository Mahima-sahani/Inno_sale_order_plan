from odoo import models, fields, _, api
from odoo.exceptions import UserError


class AddProductSku(models.TransientModel):
    _name = 'inno.product.sku'
    _description = 'Used to add new New sku'

    standard_size = fields.Many2one(comodel_name='product.attribute.value', string='Standard Size',
                                    domain=[('attribute_id.name', '=', 'size')])
    manufacturing_size = fields.Many2one(comodel_name='inno.size', string='Manufacturing Size')
    finishing_size = fields.Many2one(comodel_name='inno.size', string='Finishing Size')
    sku = fields.Char(string='SKU')
    product_tmpl_id = fields.Many2one(comodel_name='product.template', string='Design',
                                      domain=[('is_raw_material', '=', False)])

    @api.onchange('standard_size')
    def onchange_standard_size(self):
        standard_size = self.standard_size.size_id
        if standard_size and standard_size.size_type:
            recs = standard_size.inno_size_line.filtered(
                lambda size: self.product_tmpl_id.division_id.id in size.division_id.ids)
            if (standard_size.size_type in ['circle', 'square']):
                size = f"{standard_size.length}{int(standard_size.len_fraction) if int(standard_size.len_fraction) else ''}"
            else:
                size = f"{standard_size.length}{int(standard_size.len_fraction) if int(standard_size.len_fraction) else ''}{standard_size.width}{int(standard_size.width_fraction) if int(standard_size.width_fraction) else ''}"
            self.write({'manufacturing_size': recs.filtered(lambda
                                                                rec: rec.size == 'manufacturing' and self.product_tmpl_id.division_id.id == rec.division_id.id).child_size_id[
                0].id if recs.filtered(lambda
                                           rec: rec.size == 'manufacturing' and self.product_tmpl_id.division_id.id == rec.division_id.id).child_size_id else False,
                        'finishing_size': recs.filtered(lambda rec: rec.size == 'finishing').child_size_id[
                            0].id if recs.filtered(lambda rec: rec.size == 'finishing').child_size_id else False,
                        'sku': f'{self.product_tmpl_id.name.replace("-", "")}-{size}'})

    def do_confirm(self):
        if (self.env['product.product'].search([('default_code', '=', self.sku)]) or
                self.env['inno.sku.product.mapper'].search([('sku', '=', self.sku)])):
            raise UserError(_("SkU is already Mapped."))
        attribute_id = self.env['product.attribute'].search([('name', '=', 'size')], limit=1)
        product_id = self.product_tmpl_id.product_variant_ids.filtered(
            lambda pv: self.standard_size.name in pv.product_template_attribute_value_ids.mapped('name'))
        if product_id:
            self.env['inno.sku.product.mapper'].create({'sku': self.sku, 'product_id': product_id.id})
        else:
            attribute_line = self.product_tmpl_id.attribute_line_ids.filtered(
                lambda al: al.attribute_id.id == attribute_id.id)
            if attribute_line:
                attribute_line.sudo().write({'value_ids': [(4, self.standard_size.id)]})
            else:
                self.sudo().product_tmpl_id.write({'attribute_line_ids': [
                    (0, 0, {'attribute_id': attribute_id.id, 'value_ids': [(4, self.standard_size.id)]})]})
            product_id = self.sudo().product_tmpl_id.product_variant_ids.filtered(
                lambda pv: self.standard_size.name in pv.product_template_attribute_value_ids.mapped('name'))
            product_id.write({'default_code': self.sku, 'shape_type': self.standard_size.size_id.size_type,
                              'inno_mrp_size_id': self.manufacturing_size.id,
                              'inno_finishing_size_id': self.finishing_size.id})
            self.sudo().generate_bm(self.product_tmpl_id, product_id)

    def generate_bm(self, design, sku):
        actual_bom = design.bom_ids.filtered(lambda bom: not bom.product_id and bom.product_tmpl_id.id == design.id)
        if not design.bom_ids or not actual_bom:
            return
        if not actual_bom.bom_line_ids:
            return
        new_bom = actual_bom.sudo().copy()
        new_bom.product_id = sku.id
        for line in new_bom.bom_line_ids:
            line.product_qty = line.product_qty * sku.mrp_area

# class Rndfinishing_wiz(models.TransientModel):
#     _name = 'inno.sku.line.wiz'
#     _description = 'Used to add new New sku'
