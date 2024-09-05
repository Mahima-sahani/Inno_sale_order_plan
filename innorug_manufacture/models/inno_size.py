from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, MissingError


class InnoSize(models.Model):
    _name = 'inno.size'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Research of the new size'

    name = fields.Char("Size Name")
    shape = fields.Selection(
        selection=[('rectangular', 'Rectangular'), ('square', 'square'), ('runner', 'Runner'), ('round', "Round"),
                   ('oval', "Oval")
            , ('octagon', "Octagon"), ('star', "Star"), ('heart', "Heart"), ('kidney', "Kidney")], string="Shape")
    size_type = fields.Selection(selection=[('rectangular', 'Rectangular'), ('corner', 'Corner'), ('cut', 'Cut'),
                                            ('kidney', 'Kidney'), ('octagon', 'Octagon'), ('others', 'Others'),
                                            ('oval', 'Oval'), ('shape', 'Shape'), ('shape_p', 'Shape P'),
                                            ('square', 'Square'), ('star', 'Star'), ('circle', 'Circle'),
                                            ('hmt', 'HMT'), ('shape_r', 'Shape R')],
                                 string='Shape', tracking=True, default='rectangular')
    state = fields.Selection(selection=[('draft', 'Draft'),
                                            ('done', 'Done') ], string='Draft', tracking=True)
    is_active = fields.Boolean()
    length = fields.Integer("Length", tracking= True)
    len_fraction = fields.Float("Length Fraction", tracking= True)
    width = fields.Integer("Width",  tracking= True)
    width_fraction = fields.Float("Width Fraction", tracking= True)
    height = fields.Integer("Height",  tracking= True)
    height_fraction = fields.Float("Height fraction",  tracking= True)
    area = fields.Float("Area(Sq.Feet)",  tracking=True, digits=(12, 4))
    perimeter = fields.Float("Perimeter", tracking=True, digits=(12, 4))
    area_sq_yard = fields.Float(string="Area(Sq. Yard)", compute="get_area_sq_yard", digits=(12, 4), store=True)
    inno_size_line = fields.One2many("inno.size.line", "inno_size_id",)
    size = fields.Selection(selection=[('standard', 'Standard')], default="standard", string='Size',)
    is_child = fields.Boolean()
    refer_size = fields.Char("Refer Size")
    active = fields.Boolean(default = True)
    abbr = fields.Char(string="Abr")
    len_parm = fields.Float("length", tracking=True, digits=(12, 4))
    width_parm = fields.Float("Width", tracking=True, digits=(12, 4))
    area_sq_mt = fields.Float("Area(Sq.Meter)", tracking=True, compute="get_area_sq_yard",digits=(12, 4))
    update_binding_gacchai = fields.Boolean(default=True)
    area_cm = fields.Float("Area(CM)", tracking=True, digits=(12, 4))

    def fix_binding_and_gachai_lenght(self):
        # size = self.env['inno.size'].search([])
        for rec in self:
            len = rec.length * 2
            len_fr = (rec.len_fraction *2) // 12
            total_len = len + len_fr
            width = rec.width * 2
            width_fr = (rec.width_fraction * 2) // 12
            total_width = width + width_fr
            if not rec.update_binding_gacchai:
                if rec.size_type in ['rectangular', 'square']:
                    rec.len_parm = total_len
                    rec.width_parm = total_width
                    tt_fr =((rec.len_fraction+ rec.width_fraction) * 2)//12
                    rec.perimeter = ((rec.length + rec.width)* 2) + tt_fr
                    rec.update_binding_gacchai = True

    @api.depends('area', 'perimeter')
    def get_area_sq_yard(self):
        for rec in self:
            if rec.area:
                rec.area_sq_yard = rec.area / 9
                rec.area_sq_yard = (rec.area_sq_yard // 1) + (int((round(rec.area_sq_yard % 1, 4)*16)//1)*0.0625)
                rec.area_sq_mt = rec.area /10.764
            else:
                rec.area_sq_yard = 0
                rec.area_sq_mt = 0

    # @api.onchange('length', 'len_fraction', 'width','width_fraction','height', 'height_fraction','size_type',)
    # def get_size(self):
    #     self.compute_size()

    @api.model
    def create(self, vals):
        res = super().create(vals)
        for rec in res:
            if not rec.name:
                rec.compute_size()
        return res


    def compute_size(self):
        for rec in self:
            abbr_dict = {'rectangular': '', 'circle': 'RD', 'corner': 'CO', 'cut': 'CU', 'hmt': 'HM', 'kidney': 'KD',
                         'octagon': 'OC', 'others': 'OT', 'oval': 'OV', 'shape': 'SH', 'shape_p': 'SH P',
                         'shape_r': 'SH R', 'square': 'SQ', 'star': 'ST'}
            len_fraction = rec.len_fraction / 10
            width_fraction = rec.width_fraction/10
            height_fraction = rec.height_fraction/10
            len = len_fraction + rec.length
            width = width_fraction + rec.width
            height = height_fraction + rec.height
            if rec.size_type == 'rectangular':
                if not self.update_binding_gacchai:
                    self.perimeter = 2*(len+width)
                len_fr = rec.len_fraction / 12
                width_fr = rec.width_fraction / 12
                len_ar =len_fr + rec.length
                width_ar = width_fr + rec.width
                self.area = len_ar * width_ar
                self.fix_binding_and_gachai_lenght()
            if rec.size_type == 'circle':
                abr = 'RD'
                self.abbr = abr
                if not self.update_binding_gacchai:
                    self.perimeter = 2 * 3.141 * (len/2)
                len_fr = rec.len_fraction / 12
                len_ar = len_fr + rec.length
                self.area =3.141 * (len_ar*len_ar/4)
            if rec.size_type == 'square':
                if not self.update_binding_gacchai:
                    self.perimeter = 2 * (len + width)
                len_fr = rec.len_fraction / 12
                width_fr = rec.width_fraction / 12
                len_ar = len_fr + rec.length
                width_ar = width_fr + rec.width
                self.area = len_ar * width_ar
                self.fix_binding_and_gachai_lenght()
            self.get_message()
            abr = abbr_dict.get(self.size_type)
            self.abbr = abr
            self.create_formate(abr)

    def get_message(self):
        if not self.length or not self.area or self.perimeter:
            pass
            # raise UserError(_("First, you can set the length width, area and perimeter and then save it"))

    def create_formate(self, abr):
        for rec in self:
            if self.len_fraction and self.width_fraction:
                rec.name = f'{self.length}`{int(self.len_fraction)}"X{self.width}`{int(self.width_fraction)}"{abr}'
            elif self.len_fraction:
                rec.name = f'{self.length}`{int(self.len_fraction)}"X{self.width}`{abr}'
            elif self.width_fraction:
                rec.name = f'{self.length}`X{self.width}`{int(self.width_fraction)}"{abr}'
            elif not self.len_fraction and not self.width_fraction:
                rec.name = f'{self.length}` X {self.width}`{abr}'
            if rec.name and not self.is_child:
                self.create_attribute_value()

    def create_attribute_value(self):
        attribute = self.env['product.attribute'].search([('name', '=', 'size')], limit=1)
        if self.name:
            if not attribute:
                attribute = self.env['product.attribute'].sudo().create({
                    'name': 'size',
                    'create_variant': 'always',
                })
            attribute_value = self.env['product.attribute.value'].search([
                ('attribute_id', '=', attribute.id),
                ('name', '=', self.name)
            ], limit=1)
            if not attribute_value:
                attribute_value = self.env['product.attribute.value'].sudo().create({
                    'name': self.name,
                    'attribute_id': attribute.id,
                    "size_id" : self.id
                })
            else:
                raise UserError(_('Size Already Exist'))

    def check_size(self):
        size_ids=self.env['inno.size'].search([
            ('name', '=', self.name)
        ])
        if len(size_ids) >1:
            size_id = size_ids.filtered(
                lambda wo: self.id not in wo.ids)
            size_id.refer_size = self.refer_size
            self.open_form(size_id)

    def open_form(self,size_id):
        self.env['inno.size'].search([('active', '=', False)]).unlink()
        self.active = False
        return {
            'type': 'ir.actions.act_window',
            'name': _("Sizes"),
            'view_mode': 'form',
            'res_model': 'inno.size',
            'res_id': size_id.id,
            "target": "current",
        }

    def button_action_calculated_mrp_and_finishing_size(self):
        if not self.area or not self.perimeter:
            raise UserError(_("Please set required area and perimeter"))
        # self.check_size()
        if not self.inno_size_line:
            if self.size_type in ['rectangular','square','circle']:
                divisions = self.env["mrp.division"].search([])
                record = []
                for rec in divisions:
                    vals = record.extend([self.get_shrink_size(rec, stype) for stype in ['manufacturing', 'finishing']])
                self.inno_size_line.create(record)
                self.state = 'done'
            else:
                if not self.inno_size_line:
                    self.ensure_one()
                    record = []
                    wizard_size_id = self.env['inno.size.wizards'].create({
                        'inno_size_id': self.id,
                    })
                    divisions = self.env["mrp.division"].search([])
                    for rec in divisions:
                        vals = record.extend(
                            [self.create_lines(rec, wizard_size_id, stype) for stype in ['manufacturing', 'finishing']])
                    wizard_size_id.size_wizards_lines.create(record)
                    return {
                        'type': 'ir.actions.act_window',
                        'name': _("Sizes"),
                        'view_mode': 'form',
                        'view_id': self.env.ref('innorug_manufacture.view_child_sizes_form').id,
                        'res_model': 'inno.size.wizards',
                        'res_id': wizard_size_id.id,
                        "target": "new",
                    }

    def create_lines(self, division, wizard_id,size_type):
        return {'division_id': division.id, 'size': size_type, 'size_wizards_id': wizard_id.id,}

    def get_shrink_size(self, division, size_type):
        if size_type == 'manufacturing':
            len_to_srink = division.shrink_mrp_length
            wid_to_srink = division.shrink_mrp_width
        elif size_type == 'finishing':
            len_to_srink = division.shrink_finishing_length
            wid_to_srink = division.shrink_finishing_width
        else:
            len_to_srink = 0.0
            wid_to_srink = 0.0
        len_in_inch = ((self.length * 12) + self.len_fraction) - len_to_srink
        wid_in_inch = ((self.width * 12) + self.width_fraction) - wid_to_srink
        inno_size_id = self.env['inno.size'].create({
            'length': len_in_inch//12,
            'len_fraction': len_in_inch%12,
            "width": wid_in_inch//12,
            'width_fraction': wid_in_inch%12,
            "is_child" : True,
            'shape' : self.shape,
            'size_type': self.size_type
        })
        inno_size_id.compute_size()
        return {'division_id': division.id, 'size': size_type, 'child_size_id': inno_size_id.id, 'inno_size_id': self.id}


class InnoSize_line(models.Model):
    _name = 'inno.size.line'

    inno_size_id = fields.Many2one("inno.size", string="Standard Size", readonly=True, store=True)
    child_size_id =fields.Many2one(comodel_name="inno.size", string="Size")
    size_type = fields.Selection(related="inno_size_id.size_type", string='Shape', tracking=True)
    size = fields.Selection(selection=[('manufacturing', 'Manufacturing'),
                                       ('finishing', 'Finishing')], string='Type', )
    division_id = fields.Many2one(comodel_name="mrp.division", string="Division")
    length = fields.Integer("Length", tracking=True)
    len_fraction = fields.Float("Length Fraction", tracking=True)
    width = fields.Integer("Width", tracking=True)
    width_fraction = fields.Float("Width Fraction", tracking=True)
    area = fields.Float("Area(Sq.Feet)", tracking=True)
    perimeter = fields.Float("Perimeter", tracking=True)


class Atrribute_line(models.Model):
    _inherit = 'product.attribute.value'

    size_id = fields.Many2one(comodel_name="inno.size")



