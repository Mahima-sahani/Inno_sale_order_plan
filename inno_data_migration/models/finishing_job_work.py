from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, MissingError
import base64
from datetime import datetime, timedelta


class FinishingJobWork(models.Model):
    _inherit = 'finishing.work.order'

    old_order_no = fields.Char(string='Old Order Number')
