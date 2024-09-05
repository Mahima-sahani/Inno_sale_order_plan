from odoo import models, fields


class StockMoveLine(models.Model):
    _inherit = 'stock.move.line'

    package_weight = fields.Float(string='Weight')
