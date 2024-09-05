from odoo import fields, models, _,api
from datetime import datetime, timedelta
from odoo.exceptions import UserError, ValidationError, MissingError
import logging
_logger = logging.getLogger(__name__)


class MrpBom(models.Model):
    _inherit = "mrp.bom"


    mrp_rug_lines = fields.One2many("mrp.rug.bom.lines", "bom_id", string="Rug lines")


    def calculate_area(self, data):
        area = 0
        size = data
        split_size = size.split("X")
        lists = []
        for i in split_size:
            m = i.split("`")
            for x in m:
                a = x.split('"')
                lists.append(a)
        rec0 = 0
        if lists[0]:
            for i in lists[0]:
                    rec0 = int(i)*12
        ans1 =0
        if lists[1]:
                for i in lists[1]:
                    k=0
                    if i:
                        k = int(i) + rec0
                        ans1 = k/36
        rec2 =2
        if lists[2]:
            for i in lists[2]:
                    rec2 = int(i)*12
        ans2 =0
        if lists[3]:
                for i in lists[3]:
                    k=0
                    if i:
                        k = int(i) + rec2
                        ans2 = k/36
        area =(ans1*ans2)
        return area



    def button_action_for_apply_varient(self):
        _logger.info("~~~~~~~1~~~~~%r~~~~~~~~", self.product_tmpl_id)
        if self.mrp_rug_lines:
            for rec in self.bom_line_ids :
                rec.unlink()
            _logger.info("~~~~~~~1~~~~~%r~~~~~~~", self.product_tmpl_id)
            if self.product_tmpl_id :
                for rec in self.product_tmpl_id.attribute_line_ids:
                    for lines in rec.value_ids:
                        area = 0
                        area =  self.calculate_area(lines.name)
                        attr_obj =self.env['product.template.attribute.value']
                        mrp_attr_id = attr_obj.search([('name','=', lines.name)])
                        for data in self.mrp_rug_lines:
                            bom_line_id = self.env["mrp.bom.line"].create({
                                    "product_id" : data.product_id.id,
                                    "product_qty" : data.product_qty * area,
                                    "product_uom_id" : data.product_uom_category_id.id,
                                    "bom_product_template_attribute_value_ids": mrp_attr_id.ids,
                                    "operation_id": data.operation_id.id,
                                    "bom_id": self.id,
                                    "parent_product_tmpl_id" : self.product_tmpl_id.id
                            })
                            if bom_line_id:
                                self.bom_line_ids += bom_line_id


class MrpRugBom(models.Model):
    _name = "mrp.rug.bom.lines"
    _description = 'Job Work'
    _inherit = ['mail.thread','mail.activity.mixin']

    product_id = fields.Many2one('product.product', 'Component', required=True)
    product_qty = fields.Float(string="Quantity")
    product_uom_category_id = fields.Many2one(related='product_id.uom_id')
    # operation_id = fields.Many2one("mrp.routing.workcenter", string="Operation")
    bom_id = fields.Many2one("mrp.bom", string="Bom")
    allowed_operation_ids = fields.One2many('mrp.routing.workcenter', related='bom_id.operation_ids')
    operation_id = fields.Many2one(
        'mrp.routing.workcenter', 'Consumed in Operation', check_company=True,
        domain="[('id', 'in', allowed_operation_ids)]",
        help="The operation where the components are consumed, or the finished products created.")

