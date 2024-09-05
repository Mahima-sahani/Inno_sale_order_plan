from odoo import fields, models, _, api
from datetime import datetime 
from odoo.exceptions import UserError, ValidationError, MissingError
import logging
_logger = logging.getLogger(__name__)


class MrpSubcontractorPricelist(models.Model):
    _name = "mrp.subcontractor.pricelist"
    _description = 'Price List'
    _inherit = ['mail.thread','mail.activity.mixin']
    
    
    name = fields.Char("Price List")
    subcontractor_id = fields.Many2one('res.partner', string='Subcontractor')
    day = fields.Float("Days")
    area_per_sqr = fields.Float("Area/Sqr")
    division_id = fields.Many2one("mrp.division", string="Division")
    product_id = fields.Many2one("product.template", string="Product")