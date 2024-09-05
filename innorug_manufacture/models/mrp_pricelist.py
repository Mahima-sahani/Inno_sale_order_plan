from odoo import fields, models, _, api
from datetime import datetime 
from odoo.exceptions import UserError, ValidationError, MissingError
import logging
_logger = logging.getLogger(__name__)


class MrpPricelist(models.Model):
    _name = "mrp.pricelist"
    _description = 'Price List'
    _inherit = ['mail.thread','mail.activity.mixin']
    
    
    name = fields.Char("Price List")
    cost_per_yard = fields.Float("Cost Sq Yard")
    division_id = fields.Many2one("mrp.division", string="Division")
    day = fields.Integer( string="Days")
    subcontractor_id = fields.Many2one('res.partner', string='Subcontractor')