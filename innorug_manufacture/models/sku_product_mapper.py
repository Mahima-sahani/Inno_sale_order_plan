from odoo import models, fields, api, _


class SkuProductMapper(models.Model):
    _name = 'inno.sku.product.mapper'
    _description = 'Map multiple skus with same product'
    _rec_name = 'sku'

    _sql_constraints = [
        ('sku_uniq', 'unique(sku)', "sku must be unique!"),
    ]

    sku = fields.Char(string='SKU')
    product_id = fields.Many2one(comodel_name='product.product', string='Product')
    product_tmpl_id = fields.Many2one(comodel_name='product.template', string='Design',
                                      related='product_id.product_tmpl_id')
