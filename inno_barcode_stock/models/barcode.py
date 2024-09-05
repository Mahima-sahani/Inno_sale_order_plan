import json
from email.utils import format_datetime
from odoo import fields, models, _, api
from datetime import datetime, timedelta
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)

class MrpWorkOrder(models.Model):
    _inherit = 'mrp.barcode'