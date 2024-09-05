from odoo import models, fields
from odoo.exceptions import UserError, ValidationError, MissingError
import io
import logging
_logger = logging.getLogger(__name__)


class MrpSaleOrder(models.TransientModel):
    _name = 'mrp.sale.order'
    _description = 'Split Process for manufacturing and purchase'
    
    
    
    file_name = fields.Char()
    data = fields.Binary(string='CSV File', required=True)