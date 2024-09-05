from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, MissingError
from datetime import datetime


class InnoResearch(models.Model):
    _name = 'inno.research'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Research of the new product'
    _rec_name = "reference"
    _order = 'id DESC'

    reference = fields.Char("Reference", default='/')
    name = fields.Char(string="name", required="1")
    date = fields.Datetime(string="Current Date", default=lambda *a: datetime.now(), readonly="1")
    product_tmpl_id = fields.Many2one(comodel_name="product.template", string="Design")
    issue_date = fields.Date(default=fields.Datetime.now)
    expected_date = fields.Date()
    state = fields.Selection(selection=[('1_draft', 'DRAFT'), ('2_process', 'Processing'), ('2_operation', 'OPERATION'),
                                        ('2_consumption_mrp', 'CONSUMPTION'),
                                        ('2_operation', 'VERIFIED'),
                                        ('3_product_sampling', 'SAMPLING'),
                                        ('4_shipment', 'SHIPPED TO CUSTOMER'), ('5_validation', 'VALIDATED'),
                                        ('6_consumption_po', 'CONSUMPTION'),
                                        ('7_rejection', 'REJECTED'),
                                        ("8_store", "STORE"), ('9_done', 'DONE'), ('cancel', 'Cancelled')],
                             default="1_draft", string="State", tracking=True)
    design = fields.Char(string="Design Name")
    is_active_purchase = fields.Boolean("Purchase")
    is_delivery = fields.Boolean("delivary")
    is_active_mrp = fields.Boolean("Manufacturing")
    is_active_verify = fields.Boolean("Verify")
    construction = fields.Many2one(comodel_name='rnd.master.data', domain=[('value_type', '=', 'construction')],
                                   string="Construction")
    image = fields.Image(string="Cad Image")
    collection = fields.Many2one(comodel_name='rnd.master.data', domain=[('value_type', '=', 'collection')],
                                 string="Collection")
    quality = fields.Many2one(comodel_name='rnd.master.data', domain=[('value_type', '=', 'quality')], string="Quality")
    quality_weight = fields.Float(string='Quality Weight', related='quality.weight', digits='Stock Weight')
    color_ways = fields.Many2one(comodel_name='rnd.master.data', domain=[('value_type', '=', 'color_ways')],
                                 string="Color Ways")
    style = fields.Many2one(comodel_name='rnd.master.data', domain=[('value_type', '=', 'style')], string="Style")
    color = fields.Many2one(comodel_name='rnd.master.data', domain=[('value_type', '=', 'color')], string="Color")
    pattern = fields.Many2one(comodel_name='rnd.master.data', domain=[('value_type', '=', 'pattern')],
                              string="Design Pattern")
    contect = fields.Many2one(comodel_name='rnd.master.data', domain=[('value_type', '=', 'contect')], string="Content")
    face_content = fields.Many2one(comodel_name='rnd.master.data', domain=[('value_type', '=', 'face_content')],
                                   string="Face Content")
    remark = fields.Text("Remarks")
    standard_cost = fields.Float(string="Standard Cost")
    origin = fields.Many2one("res.country", string="Origin",
                             default=lambda self: self.env['res.country'].search([('name', '=', 'India')], limit=1).id)
    finish_weight = fields.Float(string="Finish Weight(Per Sqr Feet)")
    hns_code = fields.Char(string="HSN")
    division_id = fields.Many2one(comodel_name="mrp.division")
    trace = fields.Selection(selection=[('quarter', 'Quarter'), ('half', 'Half'), ('full', "Full")],
                             string="Trace Type")
    map = fields.Selection(selection=[('quarter', 'Quarter'), ('half', 'Half'), ('full', "Full")], string="Map Type")
    binding_prm = fields.Selection(
        selection=[('na', 'N/A'), ('length', 'Length'), ('width', 'Width'), ('both', "Full")],
        string="Binding Parameter")
    gachhai_prm = fields.Selection(
        selection=[('na', 'N/A'), ('length', 'Length'), ('width', 'Width'), ('both', "Full")],
        string="Gachhai Parameter")
    durry_prm = fields.Selection(selection=[('na', 'N/A'), ('length', 'Length'), ('width', 'Width'), ('both', "Full")],
                                 string="Durry Parameter")
    pile_height = fields.Float(string="Pile Height(mm)")
    loop_cut = fields.Selection(selection=[('na', 'N/A'), ('loop', 'Loop'), ('cut', 'Cut'), ('both', "Both")],
                                string="Loop Cut")
    research_lines = fields.One2many(comodel_name='inno.research.line', inverse_name="research_id", )
    rnd_bom_lines = fields.One2many(comodel_name="mrp.bom.line", inverse_name="research_id", string="Bom")
    rnd_route_lines = fields.One2many(comodel_name="mrp.routing.workcenter", inverse_name="research_id",
                                      string="Operation")
    product_varients_ids = fields.Many2many(comodel_name="product.product", string="Product Varients")
    purchase_id = fields.Many2one(comodel_name="purchase.order", string="Purchase Order")
    production_id = fields.Many2one(comodel_name="mrp.production", string="Production")
    bom_id = fields.Many2one(comodel_name="mrp.bom", string="Bom")
    pick_id = fields.Many2one(comodel_name="stock.picking", string="Stock Pick")
    sequence_id = fields.Many2one(comodel_name="operation.sequence", string="Process")
    # count
    production_count = fields.Integer("Production", compute="_get_count", store=False)
    tranfer_count = fields.Integer("Transfer", compute="_get_count", store=False)
    purchase_count = fields.Integer("Purchase", compute="_get_count", store=False)
    is_main_design = fields.Boolean()
    update_product_tmpl_data = fields.Boolean(compute='update_product_template_data')

    _sql_constraints = [
        ('nameUniq', 'unique (name)', 'The design has already been created.'),
    ]

    @api.depends('product_tmpl_id.division_id', 'product_tmpl_id.construction', 'product_tmpl_id.collection',
                 'product_tmpl_id.quality', 'product_tmpl_id.color_ways', 'product_tmpl_id.style',
                 'product_tmpl_id.color', 'product_tmpl_id.pattern', 'product_tmpl_id.contect',
                 'product_tmpl_id.face_content', 'product_tmpl_id.finish_weight', 'product_tmpl_id.binding_prm',
                 'product_tmpl_id.gachhai_prm', 'product_tmpl_id.durry_prm','product_tmpl_id.pile_height')
    def update_product_template_data(self):
        for rec in self:
            if rec.product_tmpl_id:
                rec.write(
                    {'division_id': rec.product_tmpl_id.division_id.id, 'construction': rec.product_tmpl_id.construction.id,
                     'collection': rec.product_tmpl_id.collection.id, 'quality': rec.product_tmpl_id.quality.id,
                     'color_ways': rec.product_tmpl_id.color_ways.id,
                     'style': rec.product_tmpl_id.style.id, 'color': rec.product_tmpl_id.color.id,
                     'pattern': rec.product_tmpl_id.pattern.id, 'contect': rec.product_tmpl_id.contect.id,
                     'face_content': rec.product_tmpl_id.face_content.id,
                     'remark': rec.product_tmpl_id.remark, 'standard_cost': rec.product_tmpl_id.standard_cost,
                     'origin': rec.product_tmpl_id.origin.id,
                     'finish_weight': rec.product_tmpl_id.finish_weight, 'hns_code': rec.product_tmpl_id.l10n_in_hsn_code,
                     'trace': rec.product_tmpl_id.trace,
                     'map': rec.product_tmpl_id.map, 'binding_prm': rec.product_tmpl_id.binding_prm,
                     'gachhai_prm': rec.product_tmpl_id.gachhai_prm,
                     'durry_prm': rec.product_tmpl_id.durry_prm, 'pile_height': rec.product_tmpl_id.pile_height,
                     'loop_cut': rec.product_tmpl_id.loop_cut, 'update_product_tmpl_data': True})
            else:
                rec.write({'update_product_tmpl_data': False})

    @api.onchange('name')
    def check_new_design(self):
        product_id = self.env['product.template'].search([('name', '=', self.name)])
        if product_id:
            raise UserError("The design has already been created.")

    # @api.onchange('name')
    # def filter_standard_size(self):
    #     product_id = self.env['product.template'].search([('name', '=', self.name)])
    #     if product_id:
    #         raise UserError("The design has already been created.")

    def button_action_confirm(self):
        for rec in self:
            product_id = self.env['product.template'].search([('name', '=', self.name)])
            if product_id:
                raise UserError("The design has already been created.")
            if not rec.research_lines:
                raise UserError("Please Set Sample Size")
            attribute_id = self.env['product.attribute'].search([('name', '=', 'size')], limit=1)
            product_id = self.env['product.template'].search([('name', '=', rec.name)], limit=1)
            if not product_id:
                replenish_on_order_route = self.env['stock.route'].search([('name', '=', 'Replenish on Order (MTO)')],
                                                                          limit=1)
                buy_route = self.env['stock.route'].search([('name', '=', 'Buy')], limit=1)
                manufacture_route = self.env['stock.route'].search([('name', '=', 'Manufacture')], limit=1)
                uom_id = self.env['uom.uom'].search([('name', '=', 'Units')], limit=1)
                design_data = {
                    'name': rec.name, 'division_id': self.division_id.id, 'construction': self.construction.id,
                    'collection': self.collection.id, 'quality': self.quality.id, 'color_ways': self.color_ways.id,
                    'style': self.style.id, 'color': self.color.id, 'uom_id': uom_id.id, 'uom_po_id': uom_id.id,
                    'pattern': self.pattern.id, 'contect': self.contect.id, 'face_content': self.face_content.id,
                    'remark': self.remark, 'standard_cost': self.standard_cost, 'origin': self.origin.id,
                    'finish_weight': self.finish_weight, 'l10n_in_hsn_code': self.hns_code, 'trace': self.trace,
                    'map': self.map, 'binding_prm': self.binding_prm, 'gachhai_prm': self.gachhai_prm,
                    'durry_prm': self.durry_prm, 'pile_height': self.pile_height, 'loop_cut': self.loop_cut,
                    'image_1920': self.image, 'route_ids': [(4, replenish_on_order_route.id), (4, buy_route.id),
                                                            (4, manufacture_route.id)], 'sale_ok': True,
                    'purchase_ok': True,
                    'detailed_type': 'product', 'invoice_policy': 'delivery',
                    'attribute_line_ids': [(0, 0, {'attribute_id': attribute_id.id, 'value_ids':
                        [(4, self.env['product.attribute.value'].search([('attribute_id', '=', attribute_id.id),
                                                                         ('name', '=', rec.standard_size.name)],
                                                                        limit=1).id) for rec in self.research_lines]})]
                }
                product_id = self.env['product.template'].create(design_data)
                self.write({'product_tmpl_id': product_id.id, })
            if product_id:
                self.create_product_varients()
            self.write({'product_tmpl_id': product_id.id, 'state': '2_process'})

    def create_product_varients(self):
        attribute_id = self.env['product.attribute'].search([('name', '=', 'size')], limit=1)
        for rec in self.research_lines:
            if not rec.product_id:
                attribute_value = self.env['product.attribute.value'].search(
                    [('attribute_id', '=', attribute_id.id), ('name', '=', rec.standard_size.name)], limit=1)
                if not attribute_value:
                    attribute_value = self.env['product.attribute.value'].sudo().create({
                        'name': rec.standard_size.name,
                        'attribute_id': attribute_id.id,
                        "size_id": rec.standard_size.id
                    })
                sku = self.product_tmpl_id.product_variant_ids.filtered(
                    lambda pv: attribute_value.name in pv.product_template_attribute_value_ids.mapped('name'))
                if not sku:
                    self.product_tmpl_id.attribute_line_ids.filtered(
                        lambda al: al.attribute_id.id == attribute_id.id).write(
                        {'value_ids': [(4, attribute_value.id)]})
                    sku = self.product_tmpl_id.product_variant_ids.filtered(
                        lambda pv: attribute_value.name in pv.product_template_attribute_value_ids.mapped(
                            'name'))
                sku.write({'default_code': rec.name,
                           'shape_type': rec.shape,
                           'choti': rec.choti,
                           'inno_mrp_size_id': rec.manufacturing_size.id,
                           'inno_finishing_size_id': rec.finishing_size.id})
                rec.write({'product_id': sku.id})

    def button_action_cancel(self):
        production = self.env['mrp.production'].search([('research_id', '=', self.id)], limit=1)
        if production:
            for rec in production:
                rec.production_id.state = 'cancel'
        if self.purchase_id:
            self.purchase_id.state = 'cancel'
        self.state = 'cancel'

    def create_bom_design_bom(self, product_id, squ):
        order_lines = []
        if product_id:
            line_data = (0, 0, {
                "product_tmpl_id": product_id.id,
                'product_qty': 1,
                'operation_ids': [(0, 0, {"workcenter_id": rec.work_center_id.id,
                                          'name': rec.work_center_id.name, }) for rec in squ.work_center_line]
            })
            order_lines.append(line_data)
        return order_lines

    def re_sync_materials(self):
        for rec in self.product_tmpl_id.product_variant_ids:
            bom = self.product_tmpl_id.bom_ids.filtered(lambda rc: rc.product_id.id == rec.id)
            if not bom:
                new_bom = self.product_tmpl_id.bom_ids.filtered(lambda rc: not rc.product_id.id).copy()
                new_bom.write({'product_id': rec.id})
                new_bom.operation_ids.write({'research_id': False})
                new_bom.bom_line_ids.write({'research_id': False})
        boms = self.product_tmpl_id.bom_ids.filtered(lambda bom: bom.id != self.bom_id.id)
        design_components = self.bom_id.bom_line_ids
        for bom in boms:
            sku_id = bom.product_id
            operation_id = bom.operation_ids.filtered(lambda op: 'Weaving' in op.mapped('name'))
            bom.bom_line_ids.filtered(lambda bl: bl.product_id.id not in design_components.product_id.ids).unlink()
            order_lines = []
            for line in design_components:
                sku_line = bom.bom_line_ids.filtered(lambda bl: bl.product_id.id == line.product_id.id)
                if sku_line:
                    sku_line.product_qty = line.product_qty * sku_id.mrp_area
                else:
                    line_data = (0, 0, {
                        "product_id": line.product_id.id,
                        'product_qty': float(line.product_qty * sku_id.mrp_area),
                        'operation_id': operation_id.id
                    })
                    order_lines.append(line_data)
            bom.write({'bom_line_ids': order_lines
                       })

    def re_sync_operations(self):
        for rec in self.product_tmpl_id.product_variant_ids:
            bom = self.product_tmpl_id.bom_ids.filtered(lambda rc: rc.product_id.id == rec.id)
            if not bom:
                new_bom = self.product_tmpl_id.bom_ids.filtered(lambda rc: not rc.product_id.id).copy()
                new_bom.write({'product_id': rec.id})
                new_bom.operation_ids.write({'research_id': False})
                new_bom.bom_line_ids.write({'research_id': False})
        boms = self.product_tmpl_id.bom_ids.filtered(lambda bom: bom.id != self.bom_id.id)
        design_operations = self.bom_id.operation_ids
        for bom in boms:
            bom.operation_ids.filtered(
                lambda op: op.workcenter_id.id not in design_operations.workcenter_id.ids).unlink()
            for operation in design_operations:
                existing_operation = bom.operation_ids.filtered(
                    lambda op: op.workcenter_id.id == operation.workcenter_id.id)
                if existing_operation:
                    existing_operation.write({'sequence': operation.sequence})
                else:
                    bom.write({'operation_ids': [(0, 0, {'name': operation.name, 'sequence': operation.sequence,
                                                         'workcenter_id': operation.workcenter_id.id})]})

    def button_action_set_operation_and_bom(self):
        if self._context.get('type') == 'mrp':
            if self.sequence_id:
                if not self.product_tmpl_id.bom_ids:
                    self.product_tmpl_id.write(
                        {'bom_ids': self.create_bom_design_bom(self.product_tmpl_id, self.sequence_id)})
                    self.product_tmpl_id.bom_ids[0].operation_ids.write({
                        'rnd_bom_id': self.product_tmpl_id.bom_ids[0].id,
                        'bom_id': self.product_tmpl_id.bom_ids[0].id,
                        'research_id': self.id
                    })
                    self.bom_id = self.product_tmpl_id.bom_ids[0].id
                self.state = '2_consumption_mrp'
            else:
                raise UserError("Need Sequence")
        else:
            return {
                'type': 'ir.actions.act_window',
                'name': _("Purchase Order") if self._context.get('type') == 'purchase' else _("Shipping Order"),
                'view_mode': 'form',
                'view_id': self.env.ref('inno_R_and_D.view_mrp_wizard_purchase_order_form').id if self._context.get(
                    'type') == 'purchase' else self.env.ref('inno_R_and_D.view_mrp_wizard_order_shipments_form').id,
                'res_model': 'order.wizards',
                "target": "new",
                'context': "{'type': 'mrp_order'}"
            }

    def button_action_for_create_mo(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Manufacturing Order"),
            'view_mode': 'form',
            'view_id': self.env.ref('inno_R_and_D.view_mrp_wizard_order_manufacturing_form').id,
            'res_model': 'order.wizards',
            "target": "new",
            'context': "{'type': 'mrp_order'}"
        }

    def add_size_with_sku(self):
        return {
            'type': 'ir.actions.act_window',
            'name': "Add Size",
            'view_mode': 'form',
            'res_model': 'size.line',
            'target': 'new'
        }

    def accept_design_name(self):
        self.product_tmpl_id.write({'name': self.design})
        for rec in self.research_lines:
            rec._compute_product()
            rec.product_id.write({"default_code": rec.name})
        self.is_main_design = True

    @api.model
    def default_get(self, fields_list):
        rec = super().default_get(fields_list)
        if rec.get('reference') == '/':
            rec.update({'reference': self.env['ir.sequence'].next_by_code('rnd_seq') or '/'})
        return rec

    def button_add_bom_data(self):
        return {
            'type': 'ir.actions.act_window',
            'name': "Add Raw Material",
            'view_mode': 'form',
            'res_model': 'inno.rnd.bom.consumption',
            'target': 'new'
        }

    def button_add_bom_verified(self):
        if not self.rnd_bom_lines:
            raise UserError("Please add bom data")
        else:
            self.state = '2_operation'
            self.re_sync_materials()
            self.re_sync_operations()
            # designs = self.product_tmpl_id.filtered(lambda prd: not prd.is_verified)
            # verification = self.env['inno.product.verification'].search([('product_id', '=', designs.id)], limit=1)
            # if not verification:
            #     bom = self.product_tmpl_id.bom_ids.filtered(lambda bom: bom.product_tmpl_id and not bom.product_id)
            #     self.env['inno.product.verification'].sudo().create({
            #         'product_id': designs.id, 'priority': 'urgent', 'bom_id': bom.id})
            # else:
            #     verification.sudo().write({'priority': 'urgent'})
            # self._cr.commit()

    def button_action_done(self):
        for rec in self:
            rec.state = '9_done'

    def button_action_rejected(self):
        self.state = '7_rejection'

    def button_action_create_store(self):
        for rec in self:
            if not rec.design or not rec.research_lines:
                raise UserError("Please set Design and Product Size")
            else:
                products = rec.get_generate_product_and_varient(rec.design, rec.research_lines)
                if products:
                    self.state = '8_store'

    def _get_count(self):
        for rec in self:
            purchase = self.env['purchase.order'].search([('research_id', '=', rec.id)])
            productions = self.env['mrp.production'].search([('research_id', '=', rec.id)])
            transfer = self.env['stock.picking'].search([('research_id', '=', rec.id)])
            rec.purchase_count = len(purchase)
            rec.production_count = len(productions)
            rec.tranfer_count = len(transfer)

    def button_action_store(self):
        for rec in self:
            purchase = self.env['purchase.order'].search([
                ('research_id', '=', rec.id)
            ])
            if purchase and purchase.picking_ids.filtered(lambda pick: pick.state == 'done'):
                rec.state = '8_store'
            else:
                productions = self.env['mrp.production'].search([
                    ('research_id', '=', rec.id), ('state', '=', 'done'),
                ])
                if productions:
                    rec.state = '8_store'
                else:
                    raise UserError("Pending for production or purchase")

    def get_product(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Products"),
            'view_mode': 'form',
            'res_model': 'product.template',
            "target": "current",
            'res_id': self.product_tmpl_id.id,
        }

    def get_transfer(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Transfer"),
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'res_id': self.pick_id.id,
            "target": "current",
        }

    def get_purchase_order(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Purchase"),
            'view_mode': 'form',
            'res_model': 'purchase.order',
            'res_id': self.purchase_id.id,
            "target": "current",
        }

    def button_action_set_verify_bom(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Boms"),
            'view_mode': 'tree,form',
            'res_model': 'mrp.bom',
            "target": "current",
            "domain": [('research_id', '=', self.id)]
        }

    def get_manufacturing(self):
        productions = self.env['mrp.production'].search([
            ('research_id', '=', self.id),
        ])
        return {
            'type': 'ir.actions.act_window',
            'name': _("Manufacturing"),
            'view_mode': 'tree,form',
            'res_model': 'mrp.production',
            "target": "current",
            "domain": [('research_id', '=', self.id)]
        }

    def button_action_validated(self):
        self.state = '5_validation'
