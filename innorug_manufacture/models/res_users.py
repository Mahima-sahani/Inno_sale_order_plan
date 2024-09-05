from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    division_id = fields.Many2many(comodel_name='mrp.division')
    material_location_id = fields.Many2one(comodel_name='stock.location', string='Material Location',
                                           domain=[('usage', '=', 'internal')])
    storage_location_ids = fields.Many2many(comodel_name='stock.location', relation='user_store_location_relation',
                                            string='Stores', domain=[('usage', '=', 'internal')])
