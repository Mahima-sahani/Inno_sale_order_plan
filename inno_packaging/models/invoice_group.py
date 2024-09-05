from odoo import models, fields, _, api
from odoo.exceptions import UserError
class InvoiceGroup(models.Model):
    _name = 'inno.invoive.group'

    name = fields.Char("Invoice Group Name")
    hsn_code = fields.Char("ITCHS Code")
    rate = fields.Float("Rate")
    weight = fields.Float("Weight(Per Sq. Feet)")
    knots = fields.Integer("Knots")
    is_sample = fields.Boolean("Is Sample")
    is_active = fields.Boolean("Is Active")
    seperate_wieght = fields.Boolean("Seperate Weight In Invoice")
    division_id = fields.Many2one("mrp.division", string="Division")
