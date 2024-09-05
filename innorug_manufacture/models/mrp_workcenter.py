from odoo import models, fields


class MrpWorkCenter(models.Model):
    _inherit = 'mrp.workcenter'

    is_weaving_workcenter = fields.Boolean()
    location_id = fields.Many2one(comodel_name='stock.location', string="Work-Center's Location")
