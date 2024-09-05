from odoo import models, fields


class MrpBarcode(models.Model):
    _inherit = 'mrp.barcode'

    old_system_barcode = fields.Char(string="Old Barcode")
