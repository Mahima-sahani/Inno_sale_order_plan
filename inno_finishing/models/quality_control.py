from odoo import models, fields


class Barcode(models.Model):
    _inherit = 'mrp.quality.control'

    finish_jobwork_id = fields.Many2one("finishing.work.order", string="Job Work")
    jobwork_barcode_lines = fields.One2many(related="finish_jobwork_id.jobwork_barcode_lines", string="Barcodes")
    qty = fields.Integer(related="finish_jobwork_id.total_qty", string="Quantity")