from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime
import base64
import requests
import json
import logging
_logger = logging.getLogger(__name__)


class DyeingOrder(models.Model):
    _name = 'dyeing.order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Dyeing Order'

    name = fields.Char(string='Order Number')
    location_id = fields.Many2one(comodel_name='stock.location')
    partner_id = fields.Many2one(comodel_name='res.partner')
    issue_date = fields.Date(string='Issue Date')
    expected_date = fields.Date(string='Expected Date')
    dyeing_order_line_ids = fields.One2many(comodel_name='dyeing.order.line', inverse_name='dyeing_order_id')
    division_id = fields.Many2one(comodel_name='mrp.division')
    state = fields.Selection(selection=[('draft', 'Draft'), ('confirm', 'Confirm'), ('cancel', 'Cancelled'),
                                        ('partial', 'Partial Received'), ('done', 'Received')])
    material_issue_id = fields.Many2one(comodel_name='dyeing.material.issue')

    def confirm_dyeing_order(self):
        report_size = self.env.ref('inno_sale_order_plan.action_dyeing_order_report',
                                   raise_if_not_found=False).sudo()._render_qweb_pdf(
            'inno_sale_order_plan.action_dyeing_order_report',
            res_ids=self.id)[0]
        pdf2 = base64.b64encode(report_size).decode()
        attachment = self.env['ir.attachment'].create({'name': f"Dyeing Order {self.name}", 'type': 'binary',
                                                       'datas': pdf2, 'res_model': 'dyeing.order', 'res_id': self.id})
        self.message_post(body="Dyeing Plan Report", attachment_ids=[attachment.id])
        partner_api = self.env['dyeing.partner'].search([('partner_id', '=', self.partner_id.id)])
        if partner_api:
            self.update_api_data()
        self.state = 'confirm'

    def update_api_data(self):
        dyeing_line_data = []
        for rec in self.dyeing_order_line_ids:
            dyeing_line_data.append({
                'sku': rec.product_id.default_code,
                'quantity': rec.quantity,
                'rate': rec.rate,
                # 'design_id': rec.design_id.name,
                'po_no': rec.po_no

            })
        dyeing_data = {
            'name': self.name,
            'division_id': self.division_id.name,
            'order_no' : self.name,
            'issue_date': self.issue_date.strftime('%Y-%m-%d'),
            'expected_date': self.expected_date.strftime('%Y-%m-%d'),
            'partner_id': 'Surya Carpet Pvt. Ltd.',
            'line_data': dyeing_line_data
        }
        url = "https://rug.innoage.org/dyeing_order"
        payload = json.dumps({
            "params": dyeing_data
        })
        headers = {
            'Content-Type': 'application/json',
        }
        partner_api = self.env['dyeing.partner'].search([('partner_id', '=', self.partner_id.id)])
        if partner_api.api:
            response = requests.request("POST", url, headers=headers, data=payload)
            if response.status_code != 200:
                raise UserError(_(response.reason))

    def dyeing_material_issue(self):
        if self.material_issue_id:
            raise UserError(_("Material Already Issued for this order."))
        dyeing_material_issue = self.env['dyeing.material.issue'].create({'partner_id': self.partner_id.id,
                                                                          'dyeing_order_id': self.id,
                                                                          'division': self.division_id.id,
                                                                          'state': 'draft',
                                                                          'name': self.env['ir.sequence'].next_by_code(
                                                                              'dyeing.material.issue.seq')})
        self.material_issue_id = dyeing_material_issue.id
        return {
            'type': 'ir.actions.act_window',
            'name': _("Material Issue"),
            'view_mode': 'form',
            'res_model': 'dyeing.material.issue',
            'res_id': dyeing_material_issue.id,
        }

    def action_open_material_issue(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Material Issue"),
            'view_mode': 'form',
            'res_model': 'dyeing.material.issue',
            'res_id': self.material_issue_id.id
        }


class DyeingOrderLine(models.Model):
    _name = 'dyeing.order.line'
    _description = 'Dyeing Order Line'

    dyeing_order_id = fields.Many2one(comodel_name='dyeing.order')
    product_id = fields.Many2one(comodel_name='product.product', string='Product Name')
    quantity = fields.Float(digts=(10, 4), string='Quantity')
    uom_id = fields.Many2one(comodel_name='uom.uom', string='Uom')
    received_qty = fields.Float(digits=(10, 4), string='Received Qty')
    loss_qty = fields.Float(digits=(10, 4), string='Loss')
    dyeing_intend_line_no = fields.Many2one(comodel_name='dyeing.intend.line')
    rate = fields.Float(digits=(10, 4), string='Rate')
    design_id = fields.Many2one(comodel_name='product.template')
    po_no = fields.Char(string='PO Number')
    qty_to_invoice = fields.Float(digits=(10, 4), string='Qty to Invoice')
    cancel_qty = fields.Float(digits=(10, 4), string='Qty Cancel')


class DyeingMaterialIssue(models.Model):
    _name = 'dyeing.material.issue'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Dyeing Material Issue'

    name = fields.Char()
    partner_id = fields.Many2one(comodel_name='res.partner')
    dyeing_material_issue_line_ids = fields.One2many(comodel_name='dyeing.material.issue.line',
                                                     inverse_name='dyeing_material_issue_id')
    dyeing_order_id = fields.Many2one(comodel_name='dyeing.order')
    division = fields.Many2one(related='dyeing_order_id.division_id')
    state = fields.Selection(selection=[('draft', 'Draft'), ('done', 'Complete'), ('cancel', 'Cancelled')])
    remark = fields.Char(string='Remark')
    material_move_ids = fields.Many2many(comodel_name='stock.move')

    def confirm_issue(self):
        if not self.dyeing_material_issue_line_ids or not sum(
                [rec.quantity for rec in self.dyeing_material_issue_line_ids]) > 0:
            raise UserError(_('Please Check your Materials'))
        dyeing_warehouse = self.env['stock.warehouse'].search([('code', '=', 'DYE')], limit=1)
        dyeing_location = self.env['stock.location'].search(
            [('name', '=', 'Stock'), ('warehouse_id', '=', dyeing_warehouse.id)])
        if not dyeing_location:
            raise UserError(_('Ask your admin to configure Dyeing Location.'))
        if not self.env.user.material_location_id:
            raise UserError(_('Ask your admin to add materials location for you.'))
        material_moves = [{
            'name': f"Transfer : {self.name}", 'product_id': rec.product_id.id, 'product_uom_qty': rec.quantity,
            'product_uom': rec.product_id.uom_id.id, 'quantity_done': rec.quantity,
            'location_id': self.env.user.material_location_id.id, 'origin': self.name,
            'location_dest_id': dyeing_location.id} for rec in self.dyeing_material_issue_line_ids]
        moves = self.env['stock.move'].create(material_moves)
        moves._action_confirm()
        moves._action_done()
        self.write({'material_move_ids': [(4, rec.id) for rec in moves], 'state': 'done'})
        report_size = self.env.ref('inno_sale_order_plan.action_dyeing_material_issue_report',
                                   raise_if_not_found=False).sudo()._render_qweb_pdf(
            'inno_sale_order_plan.action_dyeing_material_issue_report',
            res_ids=self.id)[0]
        pdf2 = base64.b64encode(report_size).decode()
        attachment = self.env['ir.attachment'].create({'name': f"Dyeing Material {self.name}", 'type': 'binary',
                                                       'datas': pdf2, 'res_model': 'dyeing.material.issue',
                                                       'res_id': self.id})
        self.message_post(body="Dyeing Plan Report", attachment_ids=[attachment.id])


class DyeingMaterialIssueLine(models.Model):
    _name = 'dyeing.material.issue.line'
    _description = 'Dyeing Material Issue Line'

    def get_for_product(self):
        products = self.env['product.product'].search([('product_template_variant_value_ids.name', '=', 'NO Shade')])
        domain = [
            ('id', 'in', products.filtered(lambda pd: pd.product_tmpl_id.is_raw_material).ids)]
        return domain

    dyeing_material_issue_id = fields.Many2one(comodel_name='dyeing.material.issue')
    product_id = fields.Many2one(comodel_name='product.product', string='Product', domain=get_for_product,)
    quantity = fields.Float(digits=(6, 4), string='Quantity')
    uom_id = fields.Many2one(related='product_id.uom_id')
    remark = fields.Char(string='Remark')
