from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64


class InnoDyeingReceive(models.Model):
    _name = 'inno.dyeing.receive'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Dyed Material Receive'

    name = fields.Char(string='Receive No')
    receive_date = fields.Date(string='Receive Date', default=fields.Date.today)
    dyeing_receive_line_ids = fields.One2many(comodel_name='inno.dyeing.receive.line', inverse_name='dyeing_receive_id')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Dyeing House')
    job_worker_doc = fields.Char()
    data = fields.Text(string='API Data')
    division_id = fields.Many2one(comodel_name='mrp.division', string='Division')
    state = fields.Selection(selection=[('draft', 'Draft'), ('done', 'Completed'), ('cancel', 'Cancelled')],
                             default='draft')
    material_move_ids = fields.Many2many(comodel_name='stock.move')
    remark = fields.Char(string='Remark')
    bill_id = fields.Many2one(comodel_name='account.move', string='Dyeing Invoice')

    def generate_bill(self):
        tax_id = self.partner_id.property_account_position_id.tax_ids.tax_dest_id
        journal_id = self.env['inno.config'].sudo().search([], limit=1).dyeing_journal_id
        if not journal_id:
            raise UserError(_("Please ask your admin to set weaving Journal"))
        invoice_lines = [
            (0, 0, {'product_id': rec.product_id.id, 'quantity': rec.allotted_qty, 'price_unit': rec.rate,\
                    'tax_ids': [(4, tax_id.id)] if tax_id else False, 'account_id': journal_id.default_account_id.id})
            for rec in self.dyeing_receive_line_ids if rec.rate > 0.0 and rec.product_id]
        if invoice_lines:
            bill = self.env['account.move'].create({
                'move_type': 'in_invoice',
                'partner_id': self.partner_id.id,
                'date': fields.Datetime.now(),
                'invoice_date': fields.Datetime.now(),
                'invoice_line_ids': invoice_lines,
                'journal_id': journal_id.id
            })
        else:
            raise UserError(_('No Line to Invoice, Please verify !!!'))
        self.bill_id = bill.id
        report_size = self.env.ref('inno_sale_order_plan.action_dyeing_invoice_report',
                                   raise_if_not_found=False).sudo()._render_qweb_pdf(
            'inno_sale_order_plan.action_dyeing_invoice_report',
            res_ids=self.id)[0]
        pdf2 = base64.b64encode(report_size).decode()
        attachment = self.env['ir.attachment'].create({'name': f"Dyeing Invoice {self.name}", 'type': 'binary',
                                                       'datas': pdf2, 'res_model': 'inno.dyeing.receive',
                                                       'res_id': self.id})
        self.message_post(body="Dyeing Invoice", attachment_ids=[attachment.id])

    def action_open_dyeing_bill(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Dyeing Bill"),
            'view_mode': 'form',
            'res_model': 'account.move',
            'res_id': self.bill_id.id
        }

    def confirm_receiving(self):
        if not self.dyeing_receive_line_ids:
            raise UserError(_('No Receiving line found'))
        dyeing_warehouse = self.env['stock.warehouse'].search([('code', '=', 'DYE')], limit=1)
        dyeing_location = self.env['stock.location'].search(
            [('name', '=', 'Stock'), ('warehouse_id', '=', dyeing_warehouse.id)])
        if not dyeing_location:
            raise UserError(_('Ask your admin to configure Dyeing Location.'))
        if not self.env.user.material_location_id:
            raise UserError(_('Ask your admin to add materials location for you.'))
        vals = []
        for rec in self.dyeing_receive_line_ids:
            if self.division_id.id != rec.order_no.division_id.id:
                raise UserError(_('Your division does not Matched'))
            line = rec.order_no.dyeing_order_line_ids.filtered(lambda ol:
                                                               ol.product_id.id == rec.product_id.id
                                                               and ol.po_no == rec.po_no
                                                               and ol.design_id.id == rec.design_id.id)
            if not line:
                raise UserError(_(f"product {rec.product_id.default_code} not found in dyeing order number "
                                  f"{rec.order_no} for po {rec.po_no} and design {rec.design_id.name}"))
            line.write({'received_qty': line.received_qty+rec.received_qty, 'loss_qty': line.loss_qty+rec.loss_qty})
            vals.append({
                'name': f"Transfer : {self.name}", 'product_id': rec.product_id.id, 'product_uom_qty': rec.received_qty,
                'product_uom': rec.product_id.uom_id.id, 'quantity_done': rec.received_qty,
                'location_id': dyeing_location.id, 'origin': self.name,
                'location_dest_id': self.env.user.material_location_id.id})
        if vals:
            moves = self.env['stock.move'].create(vals)
            moves._action_confirm()
            moves._action_done()
            self.write({'material_move_ids': [(4, rec.id) for rec in moves], 'state': 'done'})
            report_size = self.env.ref('inno_sale_order_plan.action_dyeing_receive_report',
                                       raise_if_not_found=False).sudo()._render_qweb_pdf(
                'inno_sale_order_plan.action_dyeing_receive_report',
                res_ids=self.id)[0]
            pdf2 = base64.b64encode(report_size).decode()
            attachment = self.env['ir.attachment'].create({'name': f"Dyeing Receive {self.name}", 'type': 'binary',
                                                           'datas': pdf2, 'res_model': 'inno.dyeing.receive',
                                                           'res_id': self.id})
            self.message_post(body="Dyeing Plan Report", attachment_ids=[attachment.id])


class InnoDyeingReceiveLine(models.Model):
    _name = 'inno.dyeing.receive.line'

    dyeing_receive_id = fields.Many2one(comodel_name='inno.dyeing.receive')
    product_id = fields.Many2one(comodel_name='product.product', string='Product')
    po_no = fields.Char(string='PO Number')
    allotted_qty = fields.Float(digits=(10, 4), string='Allotted Qty')
    received_qty = fields.Float(digits=(10, 4), string='Received Qty')
    loss_qty = fields.Float(digits=(10, 4), string='Loss Qty')
    remark = fields.Char(string='Remark')
    order_line_id = fields.Many2one(comodel_name='dyeing.order.line')
    order_no = fields.Many2one(comodel_name='dyeing.order', string='Dyeing Order')
    design_id = fields.Many2one(comodel_name='product.template', string='Design')
    rate = fields.Float(digits=(10, 3), string='Rate')

    @api.onchange('received_qty', 'allotted_qty')
    def onchange_received_qty(self):
        self.loss_qty = self.allotted_qty - self.received_qty
