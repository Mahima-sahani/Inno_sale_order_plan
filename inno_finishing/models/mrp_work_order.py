from odoo import fields, models, _, api
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)

class MrpWorkOrder(models.Model):
    _inherit = 'mrp.workorder'