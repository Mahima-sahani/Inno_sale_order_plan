from odoo import fields, models, _, api


class CostCenterLine(models.Model):
    _name = "mrp.cost.center.line"
    _description = 'Cost Center Line'
    
    name = fields.Char(string="Cost Center")
    product_id =fields.Many2one(comodel_name="product.product", string="Product")
    product_qty = fields.Float(string="Allotment Qty(Units)")
    cost_center_id = fields.Many2one("main.costcenter", string="Cost Center")
    receive_qty = fields.Float(string="Received Qty", readonly="1")
    area = fields.Float(string="Area", readonly="1")
    cost_per_yard = fields.Float("Cost")
    last_baazar_date = fields.Date("Last Baazar Date")