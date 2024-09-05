from odoo import models, fields, api, _
from odoo.exceptions import UserError


class DyeingIntend(models.Model):
    _name = 'dyeing.intend'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Dyeing Intend'

    name = fields.Char(string='Intend Number')
    division = fields.Many2one(comodel_name='mrp.division', string='Division')
    dyeing_intend_line_ids = fields.One2many(comodel_name='dyeing.intend.line', inverse_name='dyeing_intend_id',
                                             string='Dyeing Intend Line')
    state = fields.Selection(selection=[('draft', 'Draft'), ('partial', 'Partial'), ('done', 'Completed')],
                             default='draft')
    product_tmpl_id = fields.Many2one(comodel_name='product.template', string='Design')
    order_no = fields.Char(string="PO Number")

    def dyeing_plan_complete(self):
        self.state = 'done'


class DyeingIntendLine(models.Model):
    _name = 'dyeing.intend.line'

    dyeing_intend_id = fields.Many2one(comodel_name='dyeing.intend', string='Dyeing Intend')
    product_id = fields.Many2one(comodel_name='product.product', string='Product')
    required_qty = fields.Float(digits=(12, 4), string='Required Qty')
    alloted_to_dyeing = fields.Float(digits=(12, 4), string='Alloted Qty')
    remaining_qty = fields.Float(digits=(12, 4), string='Remaining Qty', compute='compute_remaining_qty', store=True)
    qty_to_dyeing = fields.Float(digits=(12, 4), string='Qty to Dyeing')
    rate = fields.Float(digits=(12, 4), string='Rate')

    @api.depends('alloted_to_dyeing')
    def compute_remaining_qty(self):
        for rec in self:
            rec.remaining_qty = rec.required_qty - rec.alloted_to_dyeing
