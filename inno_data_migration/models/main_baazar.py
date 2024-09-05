from odoo import fields, models, _,api
from datetime import datetime
from odoo.exceptions import UserError
import requests
import logging
_logger = logging.getLogger(__name__)


class Product(models.Model):
    _inherit = "main.baazar"

    parallel_receive_number = fields.Char(string="Old Order Number")