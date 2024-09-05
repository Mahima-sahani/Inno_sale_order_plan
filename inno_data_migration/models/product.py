from odoo import fields, models, _,api
from datetime import datetime
from odoo.exceptions import UserError


class Product(models.Model):
    _inherit = "product.template"
    _description = "Product"

    is_bom = fields.Boolean("Bom")
    is_update = fields.Boolean("Update Product")



class Product_product(models.Model):
    _inherit = "product.product"
    _description = "Product"

    is_bom = fields.Boolean("Bom")
    is_mrp_update = fields.Boolean("Update Size")