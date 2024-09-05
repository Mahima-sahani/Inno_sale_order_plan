from odoo import models, fields, _, api
from odoo.exceptions import UserError


class InnoSizeWizard(models.TransientModel):
    _name = 'inno.size.wizards'

    inno_size_id = fields.Many2one(comodel_name="inno.size", string="Standard Size")
    shape = fields.Selection(related="inno_size_id.size_type", string="Shape")
    size_wizards_lines = fields.One2many(comodel_name="inno.size.wizards.line", inverse_name="size_wizards_id")

    def do_confirm(self):
        for rec in self.size_wizards_lines:
            if not rec.area or not rec.perimeter:
                raise UserError(_("Please set required area and perimeter"))
        self.inno_size_id.write(
            {'inno_size_line': [(0, 0, {"inno_size_id": self.inno_size_id.id, 'len_fraction': rec.len_fraction, "length": rec.length, 'width': rec.width,
                                        'width_fraction': rec.width_fraction, "area": rec.area, 'perimeter': rec.perimeter,'division_id': rec.division_id.id,'size': rec.size,
                                               'child_size_id': self.create_child_size(rec).id}) for rec in self.size_wizards_lines]})
        self.inno_size_id.state = 'done'

    def create_child_size(self, line):
         inno_size_id = self.env['inno.size'].create({
             'length': line.length,
             'len_fraction': line.len_fraction,
             "width": line.width,
             'width_fraction': line.width_fraction,
             "is_child": True,
             'shape': self.shape,
             'size_type': self.shape,
             'area': line.area,
             'perimeter': line.perimeter,
         })
         inno_size_id.compute_size()
         return inno_size_id


class InnoSizeWizardLine(models.TransientModel):
    _name = 'inno.size.wizards.line'

    child_size = fields.Char(string="Size")
    size = fields.Selection(selection=[('manufacturing', 'Manufacturing'),
                                       ('finishing', 'Finishing')], string='Type', )
    division_id = fields.Many2one(comodel_name="mrp.division", string="Division")
    length = fields.Integer("Length(Feet)", tracking=True)
    len_fraction = fields.Integer("Length Fraction(Inches)", tracking=True)
    width = fields.Integer("Width(Feet)", tracking=True)
    width_fraction = fields.Integer("Width Fraction(Inches)", tracking=True)
    area = fields.Float("Area(Sq.Feet)", tracking=True)
    perimeter = fields.Float("Perimeter(Feet)", tracking=True)
    size_wizards_id = fields.Many2one(comodel_name="inno.size.wizards")
    size_type = fields.Selection(related="size_wizards_id.shape")
    inno_size_id = fields.Many2one(related="size_wizards_id.inno_size_id")

    @api.onchange('length', 'len_fraction', 'width','width_fraction','height', 'height_fraction','size_type',)
    def get_size(self):
        self.compute_size()

    @api.depends('shape')
    def compute_size(self):
        for rec in self:
            if rec.size_type == 'oval':
                abr = 'OV'
                self.create_formate(abr)
            if rec.size_type == 'octagon':
                abr = 'Oct'
                self.create_formate(abr)
            if rec.size_type == 'star':
                abr = 'STR'
                self.create_formate(abr)
            if rec.size_type == 'heart':
                abr = 'HM'
                self.create_formate(abr)
            if rec.size_type == 'kidney':
                abr = 'KDNY'
                self.create_formate(abr)

    def create_formate(self, abr):
        for rec in self:
            if self.len_fraction and self.width_fraction:
                rec.child_size = f'{self.length}`{int(self.len_fraction)}"X{self.width}`{int(self.width_fraction)}" {abr}'
            elif self.len_fraction:
                rec.child_size = f'{self.length}`{int(self.len_fraction)}"X{self.width}` {abr}'
            elif self.width_fraction:
                rec.child_size = f'{self.length}`X{self.width}`{int(self.width_fraction)}" {abr}'
            elif not self.len_fraction and not self.width_fraction:
                rec.child_size = f'{self.length}` X {self.width}` {abr}'
