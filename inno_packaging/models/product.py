from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    invoice_group = fields.Many2one(comodel_name='inno.invoive.group', string='Invoice Group')