from odoo import fields, models, api, _
from odoo.exceptions import UserError


class FinishingUserAccess(models.Model):
    _inherit = 'user.access'

    finishing = fields.Boolean(string="Finishing")
    allowed_operation_ids = fields.Many2many("mrp.workcenter", string="Allowed Operation",
                                             domain=[('is_finishing_wc', '=', True)])
