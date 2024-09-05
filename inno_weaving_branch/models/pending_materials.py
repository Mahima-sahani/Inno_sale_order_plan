from odoo import models, fields


class PendingMaterials(models.Model):
    _inherit = 'inno.pending.material'

    Weaving_center_id = fields.Many2one(comodel_name='weaving.branch', string='Weaving Center')
