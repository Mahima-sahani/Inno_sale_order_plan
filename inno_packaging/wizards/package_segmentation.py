from odoo import models, fields,api, _
from odoo.exceptions import UserError


class PackageSegmentation(models.TransientModel):
    _name = 'package.segmentation'

    from_package = fields.Many2one(comodel_name='inno.packaging', string='From Package')
    to_package = fields.Many2one(comodel_name='inno.packaging', string='To Package')
    from_roll = fields.Integer(string='From Roll No.')
    to_roll = fields.Integer(string='To Roll No.')
    sale_id = fields.Many2one(comodel_name='sale.order', string='Sale Order')
    segmentation_by = fields.Selection(selection=[('sale', 'PO'), ('roll', 'Roll No')], default='roll')

    def confirm_segmentation(self):
        if self.from_package.id == self.to_package.id:
            raise UserError(_("From and to packages can't be same!"))
        # if self.from_package.buyer_id.id != self.to_package.buyer_id.id:
        #     raise UserError(_("Please select Packages of same buyer!"))
        if self.segmentation_by == 'sale':
            package_lines = self.from_package.stock_quant_lines.filtered(lambda ql: ql.inno_sale_id.id == self.sale_id.id)
            package_lines.write({'inno_package_id': self.to_package.id, 'is_segmented': True})
        elif self.segmentation_by == 'roll':
            package_lines = self.from_package.stock_quant_lines.filtered(lambda ql: self.from_roll <= ql.roll_no <= self.to_roll)
            package_lines.write({'inno_package_id': self.to_package.id, 'is_segmented': True})
