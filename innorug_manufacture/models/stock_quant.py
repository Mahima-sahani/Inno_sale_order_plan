from odoo import models, fields


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    opening = fields.Float(string='Opening Balance', digits=(8, 3))
