from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AddSize_line(models.TransientModel):
    _name = 'size.line'

    shape = fields.Selection(selection=[('rectangular', 'Rectangular'),
                                        ('kidney', 'Kidney'), ('octagon', 'Octagon'),
                                        ('oval', 'Oval'),
                                        ('square', 'Square'), ('star', 'Star'), ('circle', 'Circle'),
                                        ('heart', 'Heart'), ], string='Shape', default="rectangular", tracking=True)
    standard_size = fields.Many2one(comodel_name='inno.size', string="Standard Size")
    manufacturing_size = fields.Many2one(comodel_name='inno.size', string="Manufacturing Size")
    finishing_size = fields.Many2one(comodel_name='inno.size', string="Finishing Size")
    choti = fields.Integer("Choti")
    size_line_id = fields.Many2one('size.line')
    size_line = fields.One2many("size.line", 'size_line_id', string="Sku Details")

    @api.onchange('shape')
    def filter_standard_size(self):
        inno_resarch_id = self.env['inno.research'].browse(self._context.get('active_id'))
        if not inno_resarch_id.name or not inno_resarch_id.division_id:
            raise UserError("First you set the design and division name")
        self.standard_size = False
        self.manufacturing_size = False
        self.finishing_size = False
        return {'domain': {'standard_size': [('size_type', '=', self.shape), ('is_child', '=', False)]}}

    @api.onchange('standard_size')
    def check_standard_size(self):
        inno_resarch_id = self.env['inno.research'].browse(self._context.get('active_id'))
        if inno_resarch_id.research_lines.filtered(lambda rs: self.standard_size.id in rs.standard_size.ids):
            self.standard_size = False
            raise UserError("Standard size already mapped")
        if inno_resarch_id.division_id:
            if self.shape and self.standard_size:
                recs = self.standard_size.inno_size_line.filtered(
                    lambda size: inno_resarch_id.division_id.id in size.division_id.ids)
                self.write(
                    {'manufacturing_size': recs.filtered(lambda rec: rec.size == 'manufacturing')[0].child_size_id[
                        0].id if recs.filtered(lambda rec: rec.size == 'manufacturing')[0].child_size_id else False,
                     'finishing_size': recs.filtered(lambda rec: rec.size == 'finishing')[0].child_size_id[
                         0].id if recs.filtered(lambda rec: rec.size == 'finishing')[0].child_size_id.id else False})

    def confirm(self):
        inno_resarch_id = self.env['inno.research'].browse(self._context.get('active_id'))
        inno_resarch_id.write({
            'research_lines': [
                (0, 0, {'shape': rec.shape,
                        'name': '0',
                        'standard_size': rec.standard_size.id,
                        'manufacturing_size': rec.manufacturing_size.id,
                        'finishing_size': rec.finishing_size.id
                        }) for rec in self.size_line]})
        self._cr.commit()
        for rec in inno_resarch_id.research_lines:
            rec._compute_product()
        inno_resarch_id.create_product_varients()
        if inno_resarch_id.bom_id:
            inno_resarch_id.re_sync_materials()
            inno_resarch_id.re_sync_operations()
