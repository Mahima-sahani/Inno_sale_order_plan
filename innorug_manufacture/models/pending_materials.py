from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PendingMaterials(models.Model):
    _name = 'inno.pending.material'
    _description = 'Records pending materials'
    _rec_name = 'subcontractor_id'

    subcontractor_id = fields.Many2one(comodel_name='res.partner')
    material_line_ids = fields.One2many(comodel_name='inno.pending.material.line', inverse_name='material_id')
    process = fields.Selection([('weaving', 'Weaving'),
                               ('finishing', 'Finishing')],
                              string='Process', tracking=True)


class PendingMaterialRecord(models.Model):
    _name = 'inno.pending.material.line'
    _description = 'Records Pending Material Lines'

    material_id = fields.Many2one(comodel_name='inno.pending.material')
    product_id = fields.Many2one(comodel_name='product.product', string='Product')
    quantity = fields.Float(string='Quantity', digits=(12, 4))
