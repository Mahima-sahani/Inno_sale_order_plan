from odoo import models, fields


class ProductProduct(models.Model):
    _inherit = 'product.template'

    is_verified = fields.Boolean(string='Verified?')
