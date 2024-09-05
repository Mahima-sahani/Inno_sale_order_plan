from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, MissingError
import base64
from datetime import datetime, timedelta


class InnoPackaging(models.Model):
    _name = 'inno.packaging'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "name"

    def get_user_domain(self):
        domain = [
            ('id', 'in', self.env['sale.order'].search([]).partner_id.ids)]
        return domain

    name = fields.Char(string='Reference',default='/')
    buyer_id = fields.Many2one(comodel_name='res.partner', string="Buyer", domain=get_user_domain)
    job_worker_id = fields.Many2one(comodel_name='res.partner', string="Job Work")
    remark = fields.Text("Remarks")
    packing_date = fields.Date(default=fields.Datetime.now)
    uom_id = fields.Many2one("uom.uom", string="Deal Units")
    ship_method = fields.Selection([('sea', 'BY SEA'), ('air', 'BY AIR'),('truck', 'BY TRUCK'),('courier', 'COURIER')],
                              string='Ship Method',)
    carrier_method = fields.Many2one("delivery.carrier", string="Carrier Method")
    status = fields.Selection([('draft', 'DRAFT'), ('progress', 'PROGRESS'), ('invoicing', 'INVOICING'), ('done', 'DONE'),],
                              string='Status', default='draft', tracking=True)
    location_id = fields.Many2one(comodel_name='stock.location', string="Location", domain=lambda self: [('id', '=', self.env.user.storage_location_ids.ids)])
    entry_type = fields.Selection([('packaging_receive', 'PACKAGING RECEIVE')], string="Entry Type")
    stock_quant_lines = fields.One2many("stock.quant", 'inno_package_id')
    roll_no_ids = fields.One2many(comodel_name='roll.no.info', inverse_name='package_id')
    max_shipment_weight = fields.Float(digits=(10, 3), string='Packed Weight')

    @api.model
    def default_get(self, fields_list):
        rec = super().default_get(fields_list)
        if rec.get('name') == '/':
            rec.update({'name': self.env['ir.sequence'].next_by_code('inno_packaging_seq') or '/'})
        return rec

    def button_confirm(self):
        self.status = 'progress'

    def button_action_for_packaging_done(self):
        for rec in self.stock_quant_lines:
            sale_id = rec.barcode_id.sale_id
            if not sale_id:
                sale_id = rec.sale_order_id
            if not sale_id:
                sale_id = rec.inno_sale_id
            if sale_id:
                picking = sale_id.picking_ids.filtered(lambda pick: pick.state not in ['done', 'cancel'])
                picking_lines = picking.move_ids_without_package.filtered(
                    lambda line: line.product_id.id == rec.product_id.id and line.quantity_done < line.product_uom_qty)
                if picking_lines:
                    picking_lines[0].quantity_done += 1
        self.status = 'invoicing'

    def button_action_add_product(self):
        return {
            'type': 'ir.actions.act_window',
            'name': "Add Product",
            'view_mode': 'form',
            'res_model': 'package.wizard',
            'target': 'new'
        }

    def button_action_for_create_invoice(self):
        pass

    def test_print(self):
        return self.env.ref('inno_packaging.action_report_print_package_label',
                     raise_if_not_found=False).report_action(docids=self.stock_quant_lines[0].package_id.id,
                                                             data={'sale': 942,
                                                                   'package': self.stock_quant_lines[0].package_id.id,
                                                                   'barcode': self.stock_quant_lines[0].barcode_id.name,
                                                                   'group': self.stock_quant_lines[0].roll_no})


class RollNoInfo(models.Model):
    _name = 'roll.no.info'
    _description = 'Roll No'

    package_id = fields.Many2one(comodel_name='inno.packaging')
    invoice_group_id = fields.Many2one(comodel_name='inno.invoive.group')
    roll_no = fields.Integer()
