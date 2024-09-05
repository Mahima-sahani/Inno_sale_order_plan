from odoo import models, fields


class InnoConfig(models.Model):
    _inherit = 'inno.config'

    inter_warehouse_operation_id = fields.Many2one(string='Inter Warehouse Operation',
                                                   comodel_name='stock.picking.type')
