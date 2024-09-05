from odoo import fields, models, _, api
import logging
import base64
import logging

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order.line'

    finishing_material_line_id = fields.Many2one("finishing.materials")


