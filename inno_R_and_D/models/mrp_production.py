from odoo import fields, models, _, api


class MrpProduction(models.Model):
    _inherit = 'mrp.production'

    is_sample = fields.Boolean(string='Sampling')
