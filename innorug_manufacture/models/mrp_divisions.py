from odoo import fields, models, _, api
from datetime import datetime 
from odoo.exceptions import UserError, ValidationError, MissingError
import logging
_logger = logging.getLogger(__name__)


class MrpDivision(models.Model):
    _name = "mrp.division"
    _description = 'Division'
    _rec_name = "name"
    _inherit = ['mail.thread','mail.activity.mixin']
    
    
    name = fields.Char("Division")
    first_penalities = fields.Float()
    second_penalities =fields.Float()
    day = fields.Integer("Total")
    product_lines_sku = fields.One2many("product.template", "division_id", string="Products Sku")
    finishing_bom_lines = fields.One2many(comodel_name="finishing.bom.line", inverse_name="division_id", string="Bom")
    shrink_mrp_length = fields.Float("Shrink Manufacturing Length")
    shrink_mrp_width = fields.Float("Shrink Manufacturing Width")
    shrink_finishing_width = fields.Float("Shrink Finishing Width")
    shrink_finishing_length = fields.Float("Shrink Finishing Length")
    wth_materials_operatios_ids = fields.Many2many(comodel_name="mrp.workcenter", string="Without Materials")
    location_id = fields.Many2one(comodel_name='stock.location', string='Division Store')


class FinishingBomLine(models.Model):
    _name = "finishing.bom.line"

    name = fields.Char()
    product_id = fields.Many2one(comodel_name="product.product", string="Materials")
    product_qty = fields.Float("Quantity", digits='Product Unit of Measure')
    uom_id = fields.Many2one(related="product_id.uom_id", string="Units")
    work_center_id = fields.Many2one(comodel_name="mrp.workcenter", string="Operation")
    division_id = fields.Many2one(comodel_name="mrp.division", string="Finishing")
    rate = fields.Float(string="Rate", digits=(4, 2))
    extra = fields.Boolean("If Extra")
    internal = fields.Boolean("Internal")
    