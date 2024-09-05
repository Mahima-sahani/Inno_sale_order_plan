from odoo import models, fields, _, api
from odoo.exceptions import UserError
class StockQuant(models.Model):
    _inherit = 'stock.quant'

    sequence_ref = fields.Integer('Sr. No.')
    rate = fields.Float("Rate")

