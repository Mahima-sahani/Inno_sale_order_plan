from odoo import fields, models, api


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    branch_id = fields.Many2one(string='Branch', comodel_name='weaving.branch')
    is_branch_delivery = fields.Boolean(compute='compute_branch_delivery')
