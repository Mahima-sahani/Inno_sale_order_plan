from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError, MissingError


class InnoResearchline(models.Model):
    _name = 'inno.research.line'
    _description = 'Research of the SKU  new product'

    name = fields.Char("Product Name")
    product_id = fields.Many2one(comodel_name ="product.product", string="Product", store=True)
    image = fields.Image()
    research_id = fields.Many2one("inno.research", string="Research")
    is_sample = fields.Boolean("Sample Size", default=False)
    shape = fields.Selection(selection=[('rectangular', 'Rectangular'),
                                            ('kidney', 'Kidney'), ('octagon', 'Octagon'),
                                            ('oval', 'Oval'),
                                            ('square', 'Square'), ('star', 'Star'), ('circle', 'Circle'),
                                            ('heart', 'Heart'), ], string='Shape',  default="rectangular", tracking=True)
    standard_size = fields.Many2one(comodel_name='inno.size',  string="Standard Size")
    manufacturing_size = fields.Many2one(comodel_name='inno.size',string="Manufacturing Size")
    finishing_size = fields.Many2one(comodel_name='inno.size', string="Finishing Size")
    choti = fields.Integer("Choti")

    def write(self, vals):
        for rec in self:
            child_size = []
            if self.manufacturing_size and not rec.standard_size.inno_size_line.filtered(
                    lambda sl: sl.size == 'manufacturing' and sl.division_id.id == rec.research_id.division_id.id and
                               sl.child_size_id.id == rec.manufacturing_size.id):
                child_size.append((0, 0, {'child_size_id': rec.manufacturing_size.id, 'size': 'manufacturing',
                                          'division_id': rec.research_id.division_id.id}))
            if self.finishing_size and not rec.standard_size.inno_size_line.filtered(
                    lambda sl: sl.size == 'finishing' and sl.division_id.id == rec.research_id.division_id.id and
                               sl.child_size_id.id == rec.finishing_size.id):
                child_size.append((0, 0, {'child_size_id': rec.manufacturing_size.id, 'size': 'finishing',
                                          'division_id': rec.research_id.division_id.id}))
            if child_size:
                rec.standard_size.write({'inno_size_line': child_size})
        return super().write(vals)

    @api.onchange('shape')
    def filter_standard_size(self):
        if not self.research_id.name or not self.research_id.division_id:
            raise UserError("First you set the design and division name")
        self.standard_size = False
        self.manufacturing_size = False
        self.finishing_size = False
        return {'domain': {'standard_size': [('size_type', '=', self.shape),('is_child', '=', False)]}}

    @api.onchange('standard_size')
    def filter_mrp_and_finishing_size(self):
        if self.research_id.division_id:
            if self.shape and self.standard_size:
                recs = self.standard_size.inno_size_line.filtered(lambda size: self.research_id.division_id.id in size.division_id.ids)
                mrp_size =recs.filtered(lambda rec: rec.size == 'manufacturing').child_size_id.ids
                finishing_size = recs.filtered(lambda rec: rec.size == 'finishing').child_size_id.ids
                self.write({'manufacturing_size': mrp_size[0] if mrp_size else False,
                           'finishing_size': finishing_size[0] if finishing_size else False})
        else:
            raise UserError("First you select the division")

    @api.onchange('standard_size')
    def _compute_product(self):
        abbr_dict = {'rectangular': '', 'circle': 'RD', 'corner': 'CO', 'cut': 'CU', 'hmt': 'HM', 'kidney': 'KD',
                     'octagon': 'OC', 'others': 'OT', 'oval': 'OV', 'shape': 'SH', 'shape_p': 'SH P',
                     'shape_r': 'SH R', 'square': 'SQ', 'star': 'ST'}
        rname = self.research_id.design.replace("-", "") if self.research_id.design else self.research_id.name.replace("-", "")
        if (self.standard_size.size_type in ['circle','square',]):
            size = f"{self.standard_size.length}{int(self.standard_size.len_fraction) if int(self.standard_size.len_fraction) else ''}"
        else:
            size = f"{self.standard_size.length}{int(self.standard_size.len_fraction) if int(self.standard_size.len_fraction) else ''}{self.standard_size.width}{int(self.standard_size.width_fraction) if int(self.standard_size.width_fraction )else ''}"
        self.name = f'{rname}-{size}{abbr_dict.get(self.standard_size.size_type)}'



    def confirm(self):
        pass

