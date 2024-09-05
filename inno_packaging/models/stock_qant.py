from odoo import models, fields, _, api
from odoo.exceptions import UserError


class StockQuant(models.Model):
    _inherit = 'stock.quant'

    inno_package_id = fields.Many2one("inno.packaging")
    barcode_id = fields.Many2one("mrp.barcode")
    sale_order_id = fields.Many2one("sale.order", string="Sale Order")
    roll_no = fields.Integer(string="Roll No")
    invoice_group_id = fields.Many2one("inno.invoive.group", string="Invoice Group")
    deal_qty = fields.Float(digits=(10, 3), string="Deal Qty")
    is_sample = fields.Boolean(string='Is Sample?')
    net_weight = fields.Float(digits=(10, 3))
    gross_weight = fields.Float(digits=(10, 3))
    inno_sale_id = fields.Many2one(comodel_name='sale.order', string='Related Sale Order')
    is_segmented = fields.Boolean()
    area_sq_yard = fields.Float(related='product_id.product_template_attribute_value_ids.product_attribute_value_id.size_id.area_sq_yard')
    area_sq_feet = fields.Float(related='product_id.product_template_attribute_value_ids.product_attribute_value_id.size_id.area')

    def button_delete_record(self):
        if self.barcode_id:
            self.barcode_id.state = '8_done'
        self.sudo().unlink()
