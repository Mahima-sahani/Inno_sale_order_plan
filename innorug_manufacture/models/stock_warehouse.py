from odoo import fields, models, _, api
from datetime import datetime

import logging
_logger = logging.getLogger(__name__)

class MrpStockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    site_name = fields.Char(string="Site Name")
    address = fields.Char(string="Address Details")





    # @api.model
    # def create(self, vals):
    #     print(vals)
    #     vals ['partner_id'] = self.id
    #     return super('MrpStockWarehouse', self).create(vals)
      
