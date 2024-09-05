from odoo import fields, models, _, api


class StcckLot(models.Model):
    _inherit = 'stock.lot'

    receive_line_id = fields.Many2one("inno.receive.line")