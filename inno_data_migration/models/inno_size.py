from odoo import fields, models, _,api
from datetime import datetime
from odoo.exceptions import UserError
import requests
import logging
_logger = logging.getLogger(__name__)


class ProductSize(models.Model):
    _inherit = "inno.size"


    is_correct = fields.Boolean()
