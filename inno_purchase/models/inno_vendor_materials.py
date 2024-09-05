import base64
from odoo import fields, models, _, api
from odoo.exceptions import UserError
from datetime import timedelta
from dateutil import relativedelta
from datetime import datetime


class InnoVendorMaterial(models.Model):
    _name = "inno.vendor.material"
    _description = 'Production Materials'
    _rec_name = "name"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id DESC'


    name = fields.Char()
    partner_id = fields.Many2one(comodel_name='res.partner')
    vendor_materials_line_ids = fields.One2many(comodel_name='inno.vendor.material.line',
                                                     inverse_name='vendor_material_issue_id')
    inno_purchase_id = fields.Many2one("inno.purchase", string="Order No")
    state = fields.Selection(selection=[('draft', 'Draft'), ('done', 'Complete'), ('cancel', 'Cancelled')])
    remark = fields.Char(string='Remark')
    material_move_ids = fields.Many2many(comodel_name='stock.move')

    def confirm_issue(self):
        if not self.vendor_materials_line_ids or not sum(
                [rec.quantity for rec in self.vendor_materials_line_ids]) > 0:
            raise UserError(_('Please Check your Materials'))
        dyeing_warehouse = self.env['stock.warehouse'].search([('code', '=', 'DYE')], limit=1)
        # dyeing_location = self.env['stock.location'].search(
        #     [('name', '=', 'Stock'), ('warehouse_id', '=', dyeing_warehouse.id)])
        # if not dyeing_location:
        #     raise UserError(_('Ask your admin to configure Dyeing Location.'))
        if not self.env.user.material_location_id:
            raise UserError(_('Ask your admin to add materials location for you.'))
        material_moves = [{
            'name': f"Transfer : {self.name}", 'product_id': rec.product_id.id, 'product_uom_qty': rec.quantity,
            'product_uom': rec.product_id.uom_id.id, 'quantity_done': rec.quantity,
            'location_id': self.env.user.material_location_id.id, 'origin': self.name,
            'location_dest_id': self.env['stock.location'].search([('usage', '=', 'supplier')], limit=1).id} for rec in self.vendor_materials_line_ids]
        moves = self.env['stock.move'].create(material_moves)
        moves._action_confirm()
        moves._action_done()
        self.write({'material_move_ids': [(4, rec.id) for rec in moves], 'state': 'done'})
        report_size = self.env.ref('inno_purchase.action_sub_material_issue_report',
                                   raise_if_not_found=False).sudo()._render_qweb_pdf(
            'inno_purchase.action_sub_material_issue_report',
            res_ids=self.id)[0]
        pdf2 = base64.b64encode(report_size).decode()
        attachment = self.env['ir.attachment'].create({'name': f"Material {self.name}", 'type': 'binary',
                                                       'datas': pdf2, 'res_model': 'inno.vendor.material',
                                                       'res_id': self.id})
        self.message_post(body="Material Plan Report", attachment_ids=[attachment.id])


class VendorMaterialIssueLine(models.Model):
    _name = 'inno.vendor.material.line'
    _description = 'Vendor Material Issue Line'

    def get_for_product(self):
        products = self.env['product.product'].search([('product_template_variant_value_ids.name', '=', 'NO Shade')])
        domain = [
            ('id', 'in', products.filtered(lambda pd: pd.product_tmpl_id.is_raw_material).ids)]
        return domain

    vendor_material_issue_id = fields.Many2one(comodel_name='inno.vendor.material')
    product_id = fields.Many2one(comodel_name='product.product', string='Product', domain=get_for_product,)
    quantity = fields.Float(digits=(6, 4), string='Quantity')
    uom_id = fields.Many2one(related='product_id.uom_id')
    remark = fields.Char(string='Remark')
    location_id = fields.Many2one("stock.location", string="Location",
                                  default=lambda self: self.env.user.material_location_id.id,
                                  domain=[('usage', '=', 'internal')])