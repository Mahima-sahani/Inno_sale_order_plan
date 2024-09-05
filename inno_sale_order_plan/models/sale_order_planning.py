# -*- coding: utf-8 -*-
from odoo import models, fields, _, api
from odoo.exceptions import UserError
import logging
from datetime import datetime, timedelta
import csv
from io import StringIO
import base64

_logger = logging.getLogger(__name__)


class SuryaSaleOrder(models.Model):
    _name = 'inno.sale.order.planning'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Sale Order Planning'
    _rec_name = "order_no"
    _order = 'id DESC'

    customer_name = fields.Many2one(comodel_name="res.partner", string="Customer Name")
    order_date = fields.Date("OrderDate")
    due_date = fields.Date("DueDate")
    order_no = fields.Char("Order No")
    buyer_order_no = fields.Char("buyer_order_no")
    sale_order_id = fields.Many2one("sale.order", "Sale Order", readonly=True)



    state = fields.Selection([('draft', 'DRAFT'), ('planning', 'PLANNING'), ('authorization', 'Authorization'),
                              ('confirm', 'CONFIRM')], string='Status', default='planning')
    sale_order_planning_lines = fields.One2many("inno.sale.order.planning.line", "sale_order_planning_id",
                                                string="Sale Order Plan")
    route_id = fields.Many2one("stock.route", string="Route Details")
    assigned_to = fields.Many2one(comodel_name='res.users', tracking=True)
    ship_method = fields.Selection(string='Ship Method', selection=[('sea', 'Sea'), ('air', 'Air'),
                                                                    ('courier', 'By Courier')], default='sea')
    dyeing_order_ids = fields.Many2many(comodel_name='dyeing.intend')
    order_type = fields.Selection(selection=[('sale', 'Sale Order'), ('custom', 'Custom Order'),
                                             ('hospitality', 'Hospitality Custom'), ('local', 'Local')], default='sale')
    dyeing_intend_count = fields.Integer(compute='compute_dyeing_count')

    amd_parent_id = fields.Many2one(comodel_name='inno.sale.order.planning', tracking=True)
    amd_parent_line = fields.One2many("inno.sale.order.planning", "amd_parent_id",)
    is_amd = fields.Boolean(compute='compute_amended')

    def compute_amended(self):
        for rec in self:
            rec.is_amd = True if len(rec.amd_parent_line) > 0 else False

    def open_amended_form(self):
        return {
            'type': 'ir.actions.act_window',
            'name': "Amended",
            'view_mode': 'form',
            'res_model': 'inno.sale.order.planning',
            'res_id': self.id,
        }


    def update_sale_order_order(self):
        return {
            'name': 'Revised',
            'view_mode': 'form',
            'res_model': 'update.sale.order.wiz',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': "{'process': 'revised'}"
        }

    def generate_purchase_report(self):
        report = self.env.ref('inno_sale_order_plan.action_purchase_material_report',
                              raise_if_not_found=False).report_action(docids=self.ids)
        return report

    def compute_dyeing_count(self):
        for rec in self:
            rec.dyeing_intend_count = rec.dyeing_order_ids.__len__()

    def set_mrp_qty(self):
        for rec in self.sale_order_planning_lines:
            rec.remaining_qty = rec.product_uom_qty - (rec.purchase_qty + rec.manufacturing_qty + rec.stock_qty)
            if rec.remaining_qty > 0:
                rec.write(
                    {'manufacturing_qty': rec.product_uom_qty, 'remaining_qty': 0})

    def manger_authentication(self):
        if sum([line.remaining_qty for line in self.sale_order_planning_lines]) > 0:
            raise UserError(_("Remaining Quantity should always be zero."))
        else:
            manager = self.env.user.employee_id.parent_id.user_id
            user = self.assigned_to.id
            self.write({
                'assigned_to': manager.id if manager else self.env.user.id,
                'state': 'authorization'
            })
            if manager not in self.message_partner_ids.ids:
                self.sudo().message_subscribe([manager.partner_id.id])
            self.env['mail.activity'].create({
                'res_name': f"Re-Planning ({self.order_no})",
                'res_id': self.id,
                'res_model_id': self.env['ir.model'].sudo().search([('model', '=', 'inno.sale.order.planning')]).id,
                'user_id': manager.id if manager else self.env.user.id,
                'summary': 'Planning Verification',
                'note': f"<b>Please verify the Planning and Create the sale order.</b>",
                'activity_type_id': 4,
                'date_deadline': datetime.today() + timedelta(days=2)
            })

    def resync_bom(self):
        for rec in self.sale_order_planning_lines.product_id.product_tmpl_id:
            design_bom = rec.bom_ids.filtered(lambda bom: bom.product_id.id == False)
            if design_bom.sequence != max(rec.bom_ids.mapped('sequence')):
                design_bom.sequence = max(rec.bom_ids.mapped('sequence')) + 1
            if max(rec.bom_ids.mapped('sequence')) == 0:
                design_bom.sequence = rec.bom_ids.__len__() + 1
                count = 0
                for bom in rec.bom_ids.filtered(lambda bm: bm.id != design_bom.id):
                    bom.sequence = count
                    count += 1
            self._cr.commit()
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'type': 'success',
                'message': "Re-sequencing Successful",
            }
        }

    def validate_weaving(self):
        for rec in self.sale_order_planning_lines:
            if rec.manufacturing_qty > 0 and not rec.product_id.bom_ids.filtered(lambda bom: bom.product_id.id == rec.product_id.id).operation_ids.filtered(lambda opr: opr.workcenter_id.id == 43):
                raise UserError(_(f"weaving not found for product {rec.product_id.default_code}"))
        raise UserError(_("All products are correct"))

    def button_action_for_sale_order(self):
        if sum([line.remaining_qty for line in self.sale_order_planning_lines]) > 0:
            raise UserError(_("Remaining Quantity should always be zero."))
        self.state = 'confirm'
        sale_order_obj = self.env["sale.order"]
        sale_order_id = sale_order_obj.search([('order_no', '=', self.order_no)])
        if sale_order_id:
            raise UserError(_("Sale order for this order number already exist"))
        mrp_route_id = self.env['stock.route'].search([
            ('name', '=', 'Manufacture'),
        ], limit=1)
        buy_route_id = self.env['stock.route'].search([
            ('name', '=', 'Buy'),
        ], limit=1)
        pricelist = self.customer_name.property_product_pricelist.id
        fiscal_position = self.customer_name.property_account_position_id.id
        if not pricelist or not fiscal_position:
            raise UserError(_("Please Configure Pricelist and Fiscal position in your Customer."))
        if not sale_order_id:
            self.sale_order_id = self.env['sale.order'].create({
                'partner_id': self.customer_name.id,
                'date_order': self.order_date,
                'validity_date': self.due_date,
                'order_no': self.order_no,
                'pricelist_id': pricelist,
                'fiscal_position_id': fiscal_position
            })
        if sum([line.remaining_qty for line in self.sale_order_planning_lines]) > 0:
            raise UserError(_("Remaining Quantity should always be zero."))
        for rec in self.sale_order_planning_lines:
            if rec:
                if rec.manufacturing_qty > 0:
                    self.get_sale_order_line(self.sale_order_id, rec.manufacturing_qty, mrp_route_id.id, rec.product_id,
                                             rec.rate, rec.brand)
                if rec.purchase_qty > 0:
                    self.get_sale_order_line(self.sale_order_id, rec.purchase_qty, buy_route_id.id, rec.product_id,
                                             rec.rate, rec.brand)
                if rec.stock_qty > 0:
                    self.get_sale_order_line(self.sale_order_id, rec.stock_qty, False, rec.product_id, rec.rate, rec.brand)
        self.sale_order_id.with_context(no_confirm_mo=True).action_confirm()
        model_id = self.env['ir.model'].sudo().search([('model', '=', 'inno.sale.order.planning')]).id
        manager_activity = self.env['mail.activity'].search([('res_id', '=', self.id),
                                                             ('user_id', '=', self.assigned_to.id),
                                                             ('res_model_id', '=', model_id)], limit=1)
        if manager_activity:
            manager_activity.action_feedback(feedback="Planning Verified")
        self.create_product_planning_report()
        self._cr.commit()

    def create_product_planning_report(self):
        """
        Generate a product planing csv file.
        """
        product_data = []
        raw_material_group = ['acrlicy_yarn', 'polyster_yarn', 'jute_yarn', 'silk', 'lefa', 'nylon',
                              'wool_viscose_blend', 'woolen_yarn', 'cotton_yarn', 'yarn', 'woolen_febric',
                              'imported', 'nylon']
        material_grand_total = 0.0
        prep_data = dict()
        for mrp in self.sale_order_id.sudo().mrp_production_ids:
            # if mrp.product_id.id not in mrp.bom_id.product_id.ids:
            #     mrp.write({'bom_id': mrp.product_id.bom_ids.filtered(lambda bm: bm.product_id).id})
            total_material = 0.0
            for rec in (mrp.move_raw_ids.
                    filtered(lambda rm: rm.product_id.product_tmpl_id.raw_material_group in raw_material_group)):
                if mrp.product_id.product_tmpl_id not in prep_data.keys():
                    prep_data[mrp.product_id.product_tmpl_id] = {rec.product_id.id: {
                        'name': rec.product_id.name, 'shade': self.get_shade(rec.product_id),
                        'color': rec.product_id.color.name, 'req_qty': rec.product_uom_qty,
                        'uom': rec.product_id.uom_id.name}, 'area': mrp.product_id.mrp_area * mrp.product_uom_qty,
                        'sku': mrp.product_id.default_code}
                elif prep_data.get(mrp.product_id.product_tmpl_id).get(rec.product_id.id):
                    prep_data.get(mrp.product_id.product_tmpl_id).get(rec.product_id.id).update({
                        'req_qty': prep_data.get(mrp.product_id.product_tmpl_id).get(rec.product_id.id).get(
                            'req_qty') + rec.product_uom_qty})
                    if prep_data.get(mrp.product_id.product_tmpl_id).get(
                            'sku') and mrp.product_id.default_code not in prep_data.get(
                        mrp.product_id.product_tmpl_id).get('sku').split(','):
                        prep_data.get(mrp.product_id.product_tmpl_id).update({'area': prep_data.get(
                            mrp.product_id.product_tmpl_id).get('area') + (
                                                                                              mrp.product_id.mrp_area * mrp.product_uom_qty),
                                                                              'sku': prep_data.get(
                                                                                  mrp.product_id.product_tmpl_id).get(
                                                                                  'sku') + ',' + mrp.product_id.default_code})
                else:
                    prep_data.get(mrp.product_id.product_tmpl_id)[rec.product_id.id] = {
                        'name': rec.product_id.name, 'shade': self.get_shade(rec.product_id),
                        'color': rec.product_id.color.name, 'req_qty': rec.product_uom_qty,
                        'uom': rec.product_id.uom_id.name}
                total_material += rec.product_uom_qty
            material_grand_total += total_material
        for design, values in prep_data.items():
            area = values.get('area')
            values.pop('area')
            values.pop('sku')
            product_data.append(
                {'design': design.name, 'quality': design.quality.weight,
                 'total_material': sum([qty.get('req_qty') for qty in values.values()]),
                 'data': [dat for dat in values.values()],
                 'area': area})
        report = self.env.ref('inno_sale_order_plan.action_dyeing_plan_report',
                              raise_if_not_found=False).sudo()._render_qweb_pdf(
            'inno_sale_order_plan.action_dyeing_plan_report',
            res_ids=self.id,
            data={'records': product_data,
                  'plan_id': self.order_no,
                  'plan_date': self.order_date,
                  'total_material': material_grand_total})[0]
        pdf = base64.b64encode(report).decode()
        attachment = self.env['ir.attachment'].create({'name': f"Dyeing Plan {self.order_no}",
                                                       'type': 'binary',
                                                       'datas': pdf,
                                                       'res_model': 'inno.sale.order.planning',
                                                       'res_id': self.id,
                                                       })
        report_size = self.env.ref('inno_sale_order_plan.action_size_area_report',
                                   raise_if_not_found=False).sudo()._render_qweb_pdf(
            'inno_sale_order_plan.action_size_area_report',
            res_ids=self.id)[0]
        pdf2 = base64.b64encode(report_size).decode()
        attachment_size = self.env['ir.attachment'].create({'name': f"Weaving Plan {self.order_no}",
                                                            'type': 'binary',
                                                            'datas': pdf2,
                                                            'res_model': 'inno.sale.order.planning',
                                                            'res_id': self.id,
                                                            })
        self.message_post(body="Dyeing Plan Report", attachment_ids=[attachment.id, attachment_size.id])

    def get_shade(self, product_id):
        shade = product_id.product_template_attribute_value_ids.filtered(
            lambda al: al.attribute_id.name in ['shade', 'Shade', 'SHADE'])
        return shade[0].name if shade else 'N/A'

    def generate_dyeing_purchase(self):
        raw_material_group = ['acrlicy_yarn', 'polyster_yarn', 'jute_yarn', 'cotton_cone', 'silk', 'lefa', 'nylon',
                              'woolen_yarn', 'cotton_yarn', 'yarn']
        for design in self.sale_order_planning_lines.product_id.product_tmpl_id:
            product_data = dict()
            for mrp in (self.sale_order_id.sudo().mrp_production_ids.filtered(
                    lambda prod: prod.product_id.product_tmpl_id.id == design.id).move_raw_ids.
                    filtered(lambda rm: rm.product_id.product_tmpl_id.raw_material_group in raw_material_group)):
                actual_product_division = mrp.bom_line_id.bom_id.product_tmpl_id.division_id
                if actual_product_division not in product_data.keys():
                    product_data[actual_product_division] = {}
                if mrp.product_id.id in product_data.get(actual_product_division).keys():
                    product_qty = product_data.get(actual_product_division).get(mrp.product_id.id).get('product_qty')
                    product_data.get(actual_product_division).get(mrp.product_id.id).update(
                        {'product_qty': product_qty + mrp.product_uom_qty})
                else:
                    product_data.get(actual_product_division)[mrp.product_id.id] = {
                        'product_id': mrp.product_id.id, 'product_qty': mrp.product_uom_qty, 'taxes_id': False}
            for division, data in product_data.items():
                dyeing_intend = self.env['dyeing.intend'].create({'division': division.id, 'product_tmpl_id': design.id,
                                                                  'name': self.env['ir.sequence'].next_by_code(
                                                                      'dyeing.intend.seq'),
                                                                  'order_no': self.order_no,
                                                                  'dyeing_intend_line_ids': [
                                                                      (0, 0, {'product_id': rec.get('product_id'),
                                                                              'required_qty': rec.get('product_qty'),
                                                                              'remaining_qty': rec.get('product_qty'),
                                                                              'qty_to_dyeing': rec.get('product_qty')})
                                                                      for rec in data.values()]})
            self.write({'dyeing_order_ids': [(4, dyeing_intend.id)]})

    def action_open_purchase_order(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Purchase Order"),
            'view_mode': 'tree,form',
            'res_model': 'dyeing.intend',
            'domain': [('id', 'in', self.dyeing_order_ids.ids)],
        }

    def get_sale_order_line(self, sale_order_id, qty, route_id, product_id, rate, brand):
        order_line = self.env['sale.order.line'].create({
            'product_id': product_id.id,
            'route_id': route_id,
            'product_uom_qty': qty,
            'brand': brand,
            'order_id': sale_order_id.id,
            'price_unit': rate
        })
        if order_line:
            sale_order_id.order_line += order_line

    def action_sale_order(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Sale Order"),
            'view_mode': 'form',
            'res_model': 'sale.order',
            'res_id': self.sale_order_id.id,
        }


class SaleOrderPlanningLine(models.Model):
    _name = 'inno.sale.order.planning.line'
    _description = 'Surya Sale Order'

    product_id = fields.Many2one("product.product", string="Product", domain=[('is_raw_material', '=', False)])
    mapped_sku = fields.Many2one(comodel_name='inno.sku.product.mapper', string='Mapped SKU')
    product_uom_qty = fields.Float("Qty to Deliver")
    available_qty = fields.Float("On-Hand Qty", related="product_id.qty_available")
    manufacturing_qty = fields.Float("Manufacturing Qty")
    purchase_qty = fields.Float("Purchase Qty")
    stock_qty = fields.Float("From Warehouse")
    rate = fields.Float("Rate")
    remaining_qty = fields.Float("Un-Assigned Qty")
    buyer_up_code = fields.Char("BuyerUpcCode")
    sale_order_planning_id = fields.Many2one("inno.sale.order.planning", string="Planning Order")
    state = fields.Selection(related="sale_order_planning_id.state")
    temp_sku = fields.Char()
    total_amount = fields.Float(difits=(12, 4), string="Total Amount", compute='compute_total_amount', store=True)
    is_purchase = fields.Boolean(compute='compute_purchase_product')
    brand = fields.Char("Brand")

    revised_lines = fields.One2many("revised.sale.order.planning.line", "planning_line_id",
                                                string="Revised Lines")
    planning_line_id = fields.Many2one("inno.sale.order.planning.line", )
    is_revised = fields.Boolean(compute='compute_revised')

    ##########################################################################################
    # replace all qty with new design
    # is_replace = fields.Boolean()
    # used for cancel design line id
    # replace_line_id = fields.Many2one("inno.sale.order.planning.line", string="Replace Line")
    ######################################################################################################
    # for new product line
    is_new = fields.Boolean()

    def compute_revised(self):
        for rec in self:
            rec.is_revised = True if len(rec.revised_lines) > 0 else False

    def compute_purchase_product(self):
        for rec in self:
            if rec.product_id.variant_seller_ids:
                rec.is_purchase = True
            else:
                rec.is_purchase = False

    @api.depends('rate', 'product_uom_qty')
    def compute_total_amount(self):
        for rec in self:
            rec.total_amount = rec.rate * rec.product_uom_qty

    @api.onchange('mapped_sku')
    def onchange_mapped_sku(self):
        if self.mapped_sku:
            self.product_id = self.mapped_sku.product_id.id

    def set_purchase_qty(self):
        self.write({'manufacturing_qty': 0, 'stock_qty': 0, 'purchase_qty': self.product_uom_qty, 'remaining_qty': 0})
        return {}

    @api.onchange('manufacturing_qty', 'purchase_qty', 'stock_qty')
    def onchange_quantity(self):
        for rec in self:
            if rec.stock_qty > rec.available_qty:
                raise UserError(_("Can't allocate more quantities than available in warehouse."))
            total_assigned_qty = sum([rec.manufacturing_qty, rec.purchase_qty, rec.stock_qty])
            if rec.product_uom_qty < total_assigned_qty:
                raise UserError(_("You can't assign more quantity than given quantity."))
            rec.remaining_qty = rec.product_uom_qty - total_assigned_qty
            rec.update_buyer_upc()

    def update_buyer_upc(self):
        for rec in self:
            if rec.buyer_up_code:
                if rec.product_id.buyer_upc_code != rec.buyer_up_code:
                    rec.product_id.write({'buyer_upc_code': rec.buyer_up_code})

    def open_revised_form(self):
        return {
            'type': 'ir.actions.act_window',
            'name': "Revised",
            'view_mode': 'form',
            'res_model': 'inno.sale.order.planning.line',
            'res_id': self.id,
            'target': 'new',
        }



class RevisedPlanningLine(models.Model):
    _name = 'revised.sale.order.planning.line'
    _description = 'Revised Surya Sale Order'

    desc_manufacturing_qty = fields.Float("Desc MRP Qty")
    amended_qty = fields.Float("Amended Qty")
    update_rate = fields.Float("Rate")
    planning_line_id = fields.Many2one("inno.sale.order.planning.line", string="Planning Lines")
    revised_date = fields.Datetime(default=fields.Datetime.now, string="Date")
    reasons = fields.Text("Reasons")
    barcodes = fields.Many2many(comodel_name='mrp.barcode')


