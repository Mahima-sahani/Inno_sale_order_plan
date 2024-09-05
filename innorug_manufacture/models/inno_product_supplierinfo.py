from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, MissingError


class InnoSupplierInfo(models.Model):
    _name = 'inno.product.supplierinfo'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Product supplier information'
    _rec_name = "partner_id"


    partner_id = fields.Many2one(comodel_name="res.partner", string="Vendor")
    product_tmpl_id = fields.Many2one(comodel_name="product.template", string="Design")
    uom_id = fields.Many2one(comodel_name="uom.uom", string="Units")
    rate = fields.Float(string="Rate", digits=(4, 2))
    variant_seller_ids = fields.One2many('product.supplierinfo', 'inno_supplierinfo_id')

    def create_seller_lines(self,product_tmpl_id,vr, area, rate, rec):
        if product_tmpl_id and vr and area and rate:
            vr.write({'variant_seller_ids': [
                (0, 0, {'partner_id': rec.partner_id.id, 'price': rate, 'product_id': vr.id, 'area': area,'inno_supplierinfo_id': rec.id})]})

    def update_rate(self):
        sq_yard_id = self.env['uom.uom'].sudo().search([
            ('name', '=', "Sq. Yard")
        ], limit=1)
        sq_ft_id = self.env['uom.uom'].sudo().search([
            ('name', '=', "ft²")
        ], limit=1)
        sq_m_id = self.env['uom.uom'].sudo().search([
            ('name', '=', "m²")
        ], limit=1)
        for rec in self:
            for vr in rec.product_tmpl_id.product_variant_ids:
                line = vr.variant_seller_ids.filtered(lambda pv: rec.partner_id.id in pv.partner_id.ids and vr.id in pv.product_id.ids)
                if rec.uom_id == sq_yard_id:
                    area =vr.product_template_attribute_value_ids.product_attribute_value_id.size_id.area_sq_yard
                    rate = area * rec.rate
                    if not line:
                        rec.create_seller_lines(rec.product_tmpl_id,vr, area, rate, rec )
                    else:
                        line.price = rate
                        line.area = area
                if rec.uom_id == sq_ft_id:
                    area = vr.product_template_attribute_value_ids.product_attribute_value_id.size_id.area
                    rate = area * rec.rate
                    if not line:
                        rec.create_seller_lines(rec.product_tmpl_id, vr, area, rate, rec)
                    else:
                        line.price = rate
                        line.area = area
                if rec.uom_id == sq_m_id:
                    area = vr.product_template_attribute_value_ids.product_attribute_value_id.size_id.area_sq_mt
                    cm_area=vr.product_template_attribute_value_ids.product_attribute_value_id.size_id.area_cm
                    if cm_area > 0.00 :
                        rate = cm_area * rec.rate
                    else:
                        rate = area * rec.rate
                    if not line:
                        rec.create_seller_lines(rec.product_tmpl_id, vr, area, rate, rec)
                    else:
                        line.price = rate
                        line.area = area


class SupplierInfo(models.Model):
    _inherit = 'product.supplierinfo'

    inno_supplierinfo_id = fields.Many2one(comodel_name="inno.product.supplierinfo")
    area = fields.Float(string="Area", digits=(4, 4))