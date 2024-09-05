from odoo import fields, models, _, api
from datetime import datetime
from odoo.exceptions import UserError


class Product(models.Model):
    _inherit = "product.product"
    _description = "Product"

    shape_type = fields.Selection(selection=[('rectangular', 'Rectangular'), ('corner', 'Corner'), ('cut', 'Cut'),
                                             ('kidney', 'Kidney'), ('octagon', 'Octagon'), ('others', 'Others'),
                                             ('oval', 'Oval'), ('shape', 'Shape'), ('shape_p', 'Shape P'),
                                             ('square', 'Square'), ('star', 'Star'), ('circle', 'Circle'),
                                             ('hmt', 'HMT'), ('shape_r', 'Shape R')], string='Shape', tracking=True)
    inno_mrp_size_id = fields.Many2one("inno.size", string='Manufacturing Size')
    inno_finishing_size_id = fields.Many2one("inno.size", string='Finishing Size')
    mrp_area = fields.Float(related='inno_mrp_size_id.area_sq_yard', string="Manufacturing Area", digits=(12, 4))
    finishing_area = fields.Float(related='inno_finishing_size_id.area_sq_yard', string="Finishing Area",
                                  digits=(12, 4))
    sq_feet_area = fields.Float("Area (Sq. Feet)", related='inno_finishing_size_id.area', digits=(12, 4))
    is_size = fields.Boolean(compute='compute_size')
    rate_list_id = fields.One2many(comodel_name='inno.product.workcenter.relation', inverse_name="actual_product_id",
                                   string='Rate List')
    is_raw_material = fields.Boolean(related='product_tmpl_id.is_raw_material', string="Raw Materials")
    raw_material_group = fields.Selection(
        selection=[('yarn', 'YARN'), ('cloth', 'CLOTH'), ('wool', 'WOOL'), ('acrlicy_yarn', 'ACRLICY YARN'),
                   ('jute_yarn', 'JUTE YARN'), ('polyster_yarn', 'POLYSTER YARN'),
                   ('wool_viscose_blend', 'WOOL VISCOSE BLEND'),
                   ('woolen_febric', 'WOOLEN FEBRIC'), ('imported', 'IMPORTED'), ('cotten_dyes', 'COTTON DYES'),
                   ('third_backing_cloth', 'THIRD BACKING CLOTH'), ('silk', 'SILK'), ('tar', 'TAR'),
                   ('tharri', 'THARRI'),
                   ('lefa', 'LEFA'), ('polypropylene', 'POLYPROPYLENE'), ('nylon', 'NYLON'), ('aanga', 'AANGA'),
                   ('ready_latex_chemical', 'READY LATEX CHEMICAL'), ('latex', 'LATEX'),
                   ('cloth_cutting', 'CLOTH CUTTING'),
                   ('newar', 'NEWAR'), ('other_raw_materials', 'OTHER RAW MATERIAL'),
                   ('weaving_cloth', 'WEAVING CLOTH'),
                   ('woolen_febric', 'WOOLEN FEBRIC'), ('cotton_cone', 'COTTON CONE'),
                   ('building_hardware', 'BUILDING HARDWARE'), ('computer_hardware', 'COMPUTER HARDWARE'),
                   ('electrical', 'ELECTRICAL'), ('office_furniture', 'OFFICE FURNITURE'), ('other', 'OTHER'),
                   ('packing_material', 'PACKING MATERIAL'),('stationary', 'STATIONARY'),
                   ('cotton','COTTON')],
        string="Raw Material Group")
    mrp_size = fields.Many2one(comodel_name='inno.size', string='Map Size')
    washing_type = fields.Selection(selection=[('12/60', '12/60'), ('antique_wash', 'Antique Wash'),
                                               ('heavy_wash', 'Heavy Wash'), ('normal_wash', 'Normal Wash'),
                                               ('special_wash', 'Special Wash')])
    choti = fields.Integer("Choti")
    trace_map_id = fields.Many2one(comodel_name='product.product', string="Trace Map")
    changeable_cloth = fields.Boolean(string='Changeable cloth?')
    buyer_upc_code = fields.Char(string="Buyer's UPC Code")
    buyer_specification = fields.Char(string="Buyer's Specification")

    # @api.model
    # def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
    #     # Try to reverse the `name_get` structure
    #     if name:
    #         args += ['|', '|', '|', ['name', 'ilike', name], ['default_code', 'ilike', name], ['product_template_variant_value_ids.name', 'ilike', name], ['product_template_variant_value_ids.name', 'ilike', name.upper()]]
    #     return self._search(args=args, limit=limit, access_rights_uid=name_get_uid)

    def compute_size(self):
        for rec in self:
            size = False
            for attrib in rec.product_template_attribute_value_ids:
                if attrib.attribute_line_id.display_name == 'size':
                    size = attrib.name or False
                    size_id = self.env["inno.size"].search([('name', '=', size)], limit=1)
                    temp_id = self.env["product.template"].search([('name', '=', self.name)], limit=1)
                    if temp_id.division_id:
                        recs = size_id.inno_size_line.filtered(
                            lambda size: temp_id.division_id.id in size.division_id.ids)
                        if recs:
                            for rec in recs:
                                if rec.size == 'manufacturing':
                                    self.inno_mrp_size_id = rec.child_size_id.id
                                if rec.size == 'finishing':
                                    self.inno_finishing_size_id = rec.child_size_id.id
                        else:
                            self.inno_mrp_size_id = False
                            self.inno_finishing_size_id = False

    def calculate_product_rate(self, workcenter, far=False, outside=False, incentive=False):
        for rec in self:
            rate_list = rec.rate_list_id.filtered(
                lambda rl: rl.work_center_id.id == workcenter.id and rl.is_far == far and rl.is_outside == outside)
            if not rate_list:
                rate_list = rec.product_tmpl_id.rate_list_id.filtered(
                    lambda rl: rl.work_center_id.id == workcenter.id and rl.is_far == far and rl.is_outside == outside)
            price_list = rate_list[0].price_list_id if rate_list else self.env['inno.rate.list']
            if not price_list:
                return (0.00, 0.00, 0.00) if incentive else 0.00
            if rate_list.rate_group_id and price_list.product_field_id.name == 'rate_list_group':
                rate = self.get_conditional_rate(price_list, rate_list.rate_group_id.rate_list_group)
                return (rate, rate_list.fixed_incentive, rate_list.expire_incentive) if incentive else rate
            elif not rate_list.rate_group_id and price_list.product_field_id.name == 'rate_list_group':
                return (0.00, 0.00, 0.00) if incentive else 0.00
            product = self if price_list.product_field_id.model == 'product.product' else self.product_tmpl_id
            field_data = product[price_list.product_field_id.name]
            if price_list.product_field_id.ttype == 'selection':
                actual_selection = list(filter(lambda sel: sel[0] == field_data,
                                               product._fields.get(price_list.product_field_id.name).selection))
                field_data = actual_selection[0][1] if actual_selection else field_data
            if price_list.product_field_id.ttype == 'many2one':
                field_data = field_data.name
            rate = self.get_conditional_rate(price_list, field_data) if price_list.condition_required \
                else price_list.base_price + price_list.variable_price
            return (rate, rate_list.fixed_incentive, rate_list.expire_incentive) if incentive else rate

    def get_rate_list_uom(self, workcenter, far=False, outside=False):
        for rec in self:
            rate_list = rec.rate_list_id.filtered(
                lambda rl: rl.work_center_id.id == workcenter.id and rl.is_far == far and rl.is_outside == outside)
            if not rate_list:
                rate_list = rec.product_tmpl_id.rate_list_id.filtered(
                    lambda rl: rl.work_center_id.id == workcenter.id and rl.is_far == far and rl.is_outside == outside)
            uom_id = rate_list.uom_id.id if rate_list else False
            return uom_id

    def get_conditional_rate(self, rate_list, field_data):
        price = 0.0
        try:
            for condition in rate_list.price_condition_ids:
                conditional_data = condition.matching_value if rate_list.product_field_id.ttype == 'float' \
                    else condition.display_value
                if ((condition.condition == '=' and field_data == conditional_data) or
                        (condition.condition == '<' and field_data < conditional_data) or
                        (condition.condition == '>' and field_data > conditional_data)):
                    price = condition.base_price + condition.variable_price
                    break
        except:
            pass
        return price


class Producttemplate(models.Model):
    _inherit = "product.template"
    _description = "Product"

    construction = fields.Many2one(comodel_name='rnd.master.data', domain=[('value_type', '=', 'construction')],
                                   string="Construction")
    image = fields.Image(string="Cad Image")
    collection = fields.Many2one(comodel_name='rnd.master.data', domain=[('value_type', '=', 'collection')],
                                 string="Collection")
    quality = fields.Many2one(comodel_name='rnd.master.data', domain=[('value_type', '=', 'quality')], string="Quality")
    color_ways = fields.Many2one(comodel_name='rnd.master.data', domain=[('value_type', '=', 'color_ways')],
                                 string="Color Ways")
    style = fields.Many2one(comodel_name='rnd.master.data', domain=[('value_type', '=', 'style')], string="Style")
    color = fields.Many2one(comodel_name='rnd.master.data', domain=[('value_type', '=', 'color')], string="Color")
    pattern = fields.Many2one(comodel_name='rnd.master.data', domain=[('value_type', '=', 'pattern')],
                              string="Design Pattern")
    contect = fields.Many2one(comodel_name='rnd.master.data', domain=[('value_type', '=', 'contect')], string="Content")
    face_content = fields.Many2one(comodel_name='rnd.master.data', domain=[('value_type', '=', 'face_content')],
                                   string="Face Content", )
    remark = fields.Text("Remarks")
    standard_cost = fields.Float(string="Standard Cost")
    origin = fields.Many2one("res.country", string="Origin")
    finish_weight = fields.Float(string="Finish Weight(Per Sqr Feet)")
    trace = fields.Selection(selection=[('quarter', 'Quarter'), ('half', 'Half'), ('full', "Full")],
                             string="Trace Type")
    map = fields.Selection(selection=[('quarter', 'Quarter'), ('half', 'Half'), ('full', "Full")], string="Map Type")
    binding_prm = fields.Selection(
        selection=[('na', 'N/A'), ('length', 'Length'), ('width', 'Width'), ('both', "Both")],
        string="Binding Parameter")
    gachhai_prm = fields.Selection(
        selection=[('na', 'N/A'), ('length', 'Length'), ('width', 'Width'), ('both', "Both")],
        string="Gachhai Parameter")
    durry_prm = fields.Selection(selection=[('na', 'N/A'), ('length', 'Length'), ('width', 'Width'), ('both', "Both")],
                                 string="Durry Parameter")
    pile_height = fields.Float(string="Pile Height(mm)")
    loop_cut = fields.Selection(selection=[('na', 'N/A'), ('loop', 'Loop'), ('cut', 'Cut'), ('both', "Both")],
                                string="Loop Cut")
    division_id = fields.Many2one("mrp.division", string="Division")
    rate_list_id = fields.One2many(comodel_name='inno.product.workcenter.relation', inverse_name="product_id",
                                   string='Rate List')
    is_raw_material = fields.Boolean("Raw Materials")
    raw_material_group = fields.Selection(
        selection=[('yarn', 'YARN'), ('cloth', 'CLOTH'), ('wool', 'WOOL'), ('acrlicy_yarn', 'ACRLICY YARN'),
                   ('jute_yarn', 'JUTE YARN'), ('polyster_yarn', 'POLYSTER YARN'),
                   ('wool_viscose_blend', 'WOOL VISCOSE BLEND'),
                   ('woolen_febric', 'WOOLEN FEBRIC'), ('imported', 'IMPORTED'), ('cotten_dyes', 'COTTON DYES'),
                   ('third_backing_cloth', 'THIRD BACKING CLOTH'), ('silk', 'SILK'), ('tar', 'TAR'),
                   ('tharri', 'THARRI'),
                   ('lefa', 'LEFA'), ('polypropylene', 'POLYPROPYLENE'), ('nylon', 'NYLON'), ('aanga', 'AANGA'),
                   ('ready_latex_chemical', 'READY LATEX CHEMICAL'), ('latex', 'LATEX'),
                   ('cloth_cutting', 'CLOTH CUTTING'),
                   ('newar', 'NEWAR'), ('other_raw_materials', 'OTHER RAW MATERIAL'),
                   ('weaving_cloth', 'WEAVING CLOTH'),
                   ('woolen_febric', 'WOOLEN FEBRIC'), ('cotton_cone', 'COTTON CONE'),
                   ('building_hardware', 'BUILDING HARDWARE'), ('computer_hardware', 'COMPUTER HARDWARE'),
                   ('electrical', 'ELECTRICAL'), ('office_furniture', 'OFFICE FURNITURE'), ('other', 'OTHER'),
                   ('packing_material', 'PACKING MATERIAL'), ('stationary', 'STATIONARY'),
                   ('cotton','COTTON')],
        string="Raw Material Group")
    with_shade = fields.Boolean(string='Purchase with Shade')
    is_spinning = fields.Boolean(string='Spinning')
    is_polytube = fields.Boolean(string='Poly Tube')

    @api.onchange('division_id')
    def apply_size(self):
        for rec in self.product_variant_ids:
            rec.compute_size()


    def update_rate_operation(self):
        if self.division_id:
            boms = self.bom_ids.filtered(lambda pr: not pr.product_id)
            if boms:
                for rec in boms.operation_ids:
                    if rec.workcenter_id.id not in self.rate_list_id.work_center_id.ids:
                        self.write({'rate_list_id' : [(0,0,{'work_center_id':rec.workcenter_id.id })]})
