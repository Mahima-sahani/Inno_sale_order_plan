from odoo import fields, models, _, api
import logging
_logger = logging.getLogger(__name__)


class BarcodeLine(models.Model):
    _name = "barcode.line"

    barcode_id = fields.Many2one("mrp.barcode", Barcode="Barcode")
    location_id = fields.Many2one(related="barcode_id.location_id")
    mrp_id = fields.Many2one(related="barcode_id.mrp_id", String="MMP ID")
    product_id = fields.Many2one(related="barcode_id.product_id", string="Product")
    transfer_id = fields.Many2one("inno.carpet.transfer")
    state = fields.Selection(related="transfer_id.state")