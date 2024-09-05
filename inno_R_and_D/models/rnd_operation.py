from odoo import models, fields, api,_


class RndOperation(models.Model):
    _name = "operation.sequence"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char("Sequence")
    work_center_line = fields.One2many(comodel_name="operation.sequence.line", inverse_name="operation_id", string="Work Center")


class RndWorkcenter(models.Model):
    _name = "operation.sequence.line"

    name = fields.Char("Sequence Line")
    work_center_id = fields.Many2one(comodel_name="mrp.workcenter", string="Operation")
    operation_id = fields.Many2one(comodel_name="operation.sequence", string="Operation")
