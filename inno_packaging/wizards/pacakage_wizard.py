from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, MissingError
from datetime import datetime
import logging

_logger = logging.getLogger(__name__)

class PackageWizard(models.TransientModel):
    _name = 'package.wizard'

    def get_user_domain(self):
        package_id = self.env['inno.packaging'].browse(self._context.get('active_id'))
        sale_orders = self.env['sale.order'].search([('partner_id', '=', package_id.buyer_id.id),('state', '=', 'sale')])
        domain = [
            ('id', 'in', sale_orders.ids)]
        return domain

    barcode_id = fields.Many2one("mrp.barcode", string="Barcode")
    id_barcode = fields.Many2one("mrp.barcode", string="Barcode")
    product_id = fields.Many2one("product.product", string="Product")
    sale_order_id = fields.Many2one("sale.order", string="Sale Order", domain=get_user_domain)
    size = fields.Many2one("inno.size", string="Specification")
    qty = fields.Float("Qty")
    deal_qty = fields.Float("Deal Qty")
    gross_weight = fields.Float("Gross Weight", compute="_compute_gross_weight")
    net_weight = fields.Float("Net Weight")
    remark = fields.Text("Remark")
    inno_package_id = fields.Many2one("inno.packaging")
    label_type = fields.Selection(selection=[('sci_label', 'SCI Label'),
                                             ('hospitality', 'Hospitality'), ('surya_qr',"Surya QR"),
                                             ('upc_label','UPC Label'),
                                             ('sci_custom',"SCI Custom"),
                                             ('livabliss','Livabliss'),
                                             ('livabliss_upc',"Livabliss UPC")])
    is_single = fields.Boolean("Single")
    is_combined = fields.Boolean("Group")
    group_qty = fields.Integer("Group Qty")
    barcode_ids = fields.Many2many(comodel_name='mrp.barcode', string='Barcodes')
    roll_no = fields.Integer("Roll No")
    invoice_group_id = fields.Many2one("inno.invoive.group", string="Invoice Group")
    is_sample = fields.Boolean(string='Is Sample?')
    packed_weight = fields.Float(digits=(10, 3))
    bale_no = fields.Integer("Roll No")

    def _compute_gross_weight(self):        
        self.gross_weight = self.qty * self.deal_qty * self.invoice_group_id.weight

    @api.onchange('product_id')
    def onchange_get_product_size(self):
        if self.product_id:
            size = self.product_id.product_template_attribute_value_ids.product_attribute_value_id.size_id
            gross_weight = 1*size.area*self.product_id.invoice_group.weight
            # net_weight = gross_weight - (((1*0.020) + (1*size.length*0.020))* 2 if size.length >= 8 else 1) - 1*size.length*0.220 if size.length >= 5e
            # net_weight = 0.0

            g_wt = self.gross_weight

            nt_wt = g_wt*6/100
            net_weight = g_wt - nt_wt

            self.write({'size': size.id, 'deal_qty': size.area, 'qty': 1,
                        'invoice_group_id': self.product_id.invoice_group.id,
                        'net_weight': net_weight, 'gross_weight': gross_weight})

    @api.onchange('sale_order_id')
    def onchange_sale_id(self):
        if self.product_id and not self.barcode_id:
            purchase_order_line = self.env['purchase.order.line'].search_count([('product_id','=',self.product_id.id),('move_ids.move_dest_ids.group_id.sale_id','=',self.sale_order_id.id)])
            if self.env['mrp.barcode'].search_count([('sale_id', '=', self.sale_order_id.id), ('state', '=', '8_done')]) == 0 and purchase_order_line == 0:
                raise UserError(_("No Quantity Available in this sale order to pack."))
            
    @api.onchange('sale_order_id')
    def onchange_label(self):
        sale_order = self.sale_order_id
        if sale_order:
            order_code = sale_order.order_no[:3]
            if order_code:
                if order_code == "HOS":
                    self.label_type = 'hospitality'

    @api.onchange('product_id')
    def onchage_livabliss_label(self):
        product_id = self.product_id
        sale_order = self.sale_order_id
        plan_order = self.env['inno.sale.order.planning'].search([('sale_order_id','=',sale_order.id)])
        rec = plan_order.sale_order_planning_lines.filtered(lambda rec: rec.product_id.id == product_id.id and rec.brand == "LIVABLISS")
        if rec:
            self.label_type = "livabliss"

    @api.onchange('invoice_group_id')
    def onchange_invoice_group_id(self):
        size = self.product_id.product_template_attribute_value_ids.product_attribute_value_id.size_id
        self.gross_weight = self.qty * self.deal_qty * self.invoice_group_id.weight

        nt_wt = self.gross_weight*6/100
        self.net_weight = self.gross_weight - nt_wt

        roll_no_id = self.inno_package_id.roll_no_ids.filtered(lambda rl: rl.invoice_group_id.id == self.invoice_group_id.id)
        self.roll_no = roll_no_id.roll_no + 1 if roll_no_id else 0

    # @api.onchange('gross_weight', 'qty')
    # def onchange_net_weight(self):
    #     self.net_weight = self.gross_weight*self.qty

    @api.onchange('barcode_id')
    def onchange_get_product_name_and_size(self):
        if self.barcode_id:
            if self.barcode_id.state in ['9_packaging', '10_done']:
                raise UserError(_("This product is already packed or delivered."))
            if self.barcode_id.state != '8_done':
                raise UserError(_("Product is not finished yet."))
            if self.barcode_id.sale_id and self.barcode_id.sale_id.partner_id.id != self.inno_package_id.buyer_id.id:
                raise UserError(_("Barcode not associated to the buyer's sale orders"))
            size = self.barcode_id.product_id.product_template_attribute_value_ids.product_attribute_value_id.size_id
            self.write({'product_id': self.barcode_id.product_id.id, 'sale_order_id': self.barcode_id.sale_id.id,
                        'size': size.id, 'deal_qty': size.area, 'qty': 1, 'invoice_group_id': self.product_id.invoice_group.id,
                        'is_sample': True if not self.barcode_id.sale_id else False,
                        'net_weight': size.area*self.product_id.invoice_group.weight})
    
    @api.onchange('id_barcode')
    def onchange_check_product_packed(self):
        if self.id_barcode:
            packing_id = self.inno_package_id
            if self.id_barcode.state not in ['9_packaging', '10_done']:
                raise UserError(_("This Product Is Not Packed Or Delivered."))
            if self.id_barcode.sale_id and self.id_barcode.sale_id.partner_id.id != self.inno_package_id.buyer_id.id:
                raise UserError(_("Barcode not associated to the buyer's sale orders"))
            
            roll = packing_id.stock_quant_lines.filtered(lambda rec: rec.barcode_id == self.id_barcode)

            size = self.id_barcode.product_id.product_template_attribute_value_ids.product_attribute_value_id.size_id
            self.write({'product_id': self.id_barcode.product_id.id, 'sale_order_id': self.id_barcode.sale_id.id,
                        'size': size.id, 'deal_qty': size.area, 'qty': 1, 'invoice_group_id': self.product_id.invoice_group.id,
                        'is_sample': True if not self.id_barcode.sale_id else False,
                        'net_weight': size.area*self.product_id.invoice_group.weight,
                        'bale_no': roll.roll_no})
            
    @api.onchange('bale_no')
    def onchange_bale_no(self):
        if self.bale_no:
            packing_no = self.inno_package_id
            record = packing_no.stock_quant_lines.filtered(lambda rec: rec.roll_no == self.bale_no)
            if record:
                if record.barcode_id:
                    self.id_barcode = record.barcode_id.id
                self.product_id = record.product_id.id
                self.sale_order_id = record.inno_sale_id.id

    def save_and_generate_label(self):
        sq = self.env['stock.quant'].search(
            [('barcode_id', '=', self.barcode_id.id)]) if self.barcode_id else False
        if sq:
            raise UserError("Already Packed")
        if self.sale_order_id.state == 'done':
            raise UserError("Already Shipped")
        if self.barcode_id and self.env['stock.quant'].search([('barcode_id', '=', self.barcode_id.id)]):
            raise UserError(_("This Product is already Packed"))
        if not self.sale_order_id and not self.is_sample:
            raise UserError(_("Product Should be sample or connected to some sale order"))
        picking = self.sale_order_id.picking_ids.filtered(lambda pick: pick.state not in ['done', 'cancel'])
        if self.sale_order_id and not self.barcode_id:
            picking_lines = picking.move_ids_without_package.filtered(
                lambda line: line.product_id.id == self.product_id.id and line.reserved_availability > line.quantity_done)
            if not picking_lines:
                raise UserError(_("No quantity available to pack"))
        roll_exist = self.inno_package_id.stock_quant_lines.filtered(lambda sq: sq.roll_no == self.roll_no)
        package = self.env['stock.quant.package'].sudo().create(
            {'sale_id': self.sale_order_id.id, 'inno_shipping_weight': self.gross_weight, 'remark': self.remark,
             'quant_ids': [
                 (0, 0, {'inno_package_id': self.inno_package_id.id, 'roll_no': self.roll_no,
                         'product_id': self.product_id.id, 'location_id': self.inno_package_id.location_id.id,
                         'deal_qty': self.deal_qty, 'quantity': self.qty, 'inno_sale_id': self.sale_order_id.id,
                         'barcode_id': self.barcode_id.id, 'invoice_group_id': self.invoice_group_id.id,
                         'is_sample': self.is_sample, 'net_weight': self.net_weight, 'gross_weight': self.gross_weight})]})
        package.write({'sale_id': self.sale_order_id.id})
        if self.sale_order_id and not package.sale_id:
            package.sale_id = self.sale_order_id.id
        self.inno_package_id.max_shipment_weight += self.gross_weight
        self.barcode_id.state = '9_packaging'
        roll_no_id = self.inno_package_id.roll_no_ids.filtered(
            lambda rl: rl.invoice_group_id.id == self.invoice_group_id.id)
        if not roll_no_id:
            self.inno_package_id.write({'roll_no_ids': [(0, 0, {'invoice_group_id': self.invoice_group_id.id,
                                                                'roll_no': self.roll_no})]})
        elif not roll_exist:
            roll_no_id.roll_no = self.roll_no
        all_package = self.env['inno.packaging'].search([('status', '=', 'progress'),
                                                         ('buyer_id', '=', self.inno_package_id.buyer_id.id)])
        packed_weight = round(sum([rec.max_shipment_weight for rec in all_package]), 3) / 100
        action = False
        if self.label_type =='sci_label':
            action = self.env.ref('inno_packaging.action_report_print_package_label',
                                raise_if_not_found=False).report_action(docids=package,
                                                                        data={'sale': self.sale_order_id.id,
                                                                                'package': package.id,
                                                                                'barcode': self.barcode_id.name,
                                                                                'group': self.roll_no})
        elif self.label_type == 'hospitality':
            action = self.env.ref('inno_packaging.action_report_print_hospitality_label',
                                raise_if_not_found=False).report_action(docids=package,
                                                                        data={'sale': self.sale_order_id.id,
                                                                                'barcode':self.barcode_id.name,
                                                                                'group': self.roll_no,
                                                                                'package': package.id})
        elif self.label_type =='surya_qr':
            action = self.env.ref('inno_packaging.action_report_print_surya_qr_label',
                                raise_if_not_found=False).report_action(docids=package,
                                                                        data={'sale': self.sale_order_id.id,
                                                                                'package': package.id,
                                                                                'barcode': self.barcode_id.name,
                                                                                'group': self.roll_no})    
        elif self.label_type =='upc_label':
            action = self.env.ref('inno_packaging.action_report_print_upc_label',
                                raise_if_not_found=False).report_action(docids=package,
                                                                        data={'sale': self.sale_order_id.id,
                                                                                'package': package.id,
                                                                                'barcode': self.barcode_id.name,
                                                                                'group': self.roll_no})
            
        elif self.label_type == 'sci_custom':
            action = self.env.ref('inno_packaging.action_report_print_sci_custom_label',
                                raise_if_not_found=False).report_action(docids=package,
                                                                        data={'sale': self.sale_order_id.id,
                                                                                'package': package.id,
                                                                                'barcode': self.barcode_id.name,
                                                                                'group': self.roll_no})
        
        elif self.label_type == 'livabliss':
            action = self.env.ref('inno_packaging.action_report_print_livabliss_label',
                                raise_if_not_found=False).report_action(docids=package,
                                                                        data={'sale': self.sale_order_id.id,
                                                                                'package': package.id,
                                                                                'barcode': self.barcode_id.name,
                                                                                'group': self.roll_no})
        elif self.label_type =='livabliss_upc':
            action = self.env.ref('inno_packaging.action_report_print_livabliss_upc_label',
                                raise_if_not_found=False).report_action(docids=package,
                                                                        data={'sale': self.sale_order_id.id,
                                                                                'package': package.id,
                                                                                'barcode': self.barcode_id.name,
                                                                                'group': self.roll_no})

        self.write({'product_id': False, 'deal_qty': False, 'sale_order_id': False, 'barcode_id': False,
                    'invoice_group_id': False, 'is_sample': False, 'size': False, 'qty': False, 'net_weight': False,
                    'gross_weight': False, 'remark': False, 'packed_weight': packed_weight})
        if self.product_id.invoice_group.id != self.invoice_group_id.id:
            self.product_id.invoice_group = self.invoice_group_id.id
        package.write({'sale_id': self.sale_order_id.id})
        return action

    def create_record_in_without_barcode_package(self, pkg):
        pkg.write({'state': 'done',
                   'quant_ids': [
                       (0, 0, {'inno_package_id': self.inno_package_id.id,
                               'roll_no': self.roll_no,
                               'product_id': self.product_id.id,
                               'location_id': pkg.location_id.id,
                               'quantity': self.deal_qty,
                               'sale_order_id': self.sale_order_id.id,
                               })]})
        return pkg

    def create_record_in_package_with_barcode(self, pkg, barcode_id):
        pkg.write({'barcode_ids': [(4, barcode_id.id)], 'state': 'done',
                      'quant_ids': [
                          (0, 0, {'inno_package_id': self.inno_package_id.id,
                                  'roll_no': self.roll_no,
                                  'product_id': self.product_id.id,
                                  'barcode_id': barcode_id.id if barcode_id else False,
                                  'location_id' : pkg.location_id.id,
                                  'quantity': self.deal_qty,
                                  'sale_order_id': self.sale_order_id.id,
                                  })]})
        return pkg

    @api.model
    def default_get(self, fields_list):
        rec = super().default_get(fields_list)
        package_id = self.env['inno.packaging'].browse(self._context.get('active_id'))
        if package_id:
            all_package = self.env['inno.packaging'].search([('status', '=', 'progress'),
                                                             ('buyer_id', '=', package_id.buyer_id.id)])
            packed_weight = round(sum([rec.max_shipment_weight for rec in all_package]), 3)/100
            rec.update({'inno_package_id': package_id.id, })
            rec.update({'packed_weight': packed_weight})
        return rec
    
    def generate_label_again(self):
        inno_package = self.inno_package_id
        if inno_package:
            if self.id_barcode:
                records = inno_package.stock_quant_lines.filtered(lambda rec: rec.barcode_id.id == self.id_barcode.id)
            else:
                records = inno_package.stock_quant_lines.filtered(lambda rec: rec.roll_no == self.bale_no)

            quant_package = records.package_id
            roll_no = records.roll_no
            if records:
                if self.label_type =='sci_label':
                    action = self.env.ref('inno_packaging.action_report_print_package_label',
                                        raise_if_not_found=False).report_action(docids=quant_package.id,
                                                                                data={'sale': self.sale_order_id.id,
                                                                                        'package': quant_package.id,
                                                                                        'barcode': self.id_barcode.name,
                                                                                        'group': roll_no})
                    
                elif self.label_type == 'hospitality':
                    action = self.env.ref('inno_packaging.action_report_print_hospitality_label',
                                        raise_if_not_found=False).report_action(docids=quant_package.id,
                                                                                data={'sale': self.sale_order_id.id,
                                                                                        'barcode':self.id_barcode.name,
                                                                                        'group': self.roll_no,
                                                                                        'package': quant_package.id})
                elif self.label_type =='surya_qr':
                    action = self.env.ref('inno_packaging.action_report_print_surya_qr_label',
                                        raise_if_not_found=False).report_action(docids=quant_package.id,
                                                                                data={'sale': self.sale_order_id.id,
                                                                                        'package': quant_package.id,
                                                                                        'barcode': self.id_barcode.name,
                                                                                        'group': roll_no})    
                elif self.label_type =='upc_label':
                    action = self.env.ref('inno_packaging.action_report_print_upc_label',
                                        raise_if_not_found=False).report_action(docids=quant_package.id,
                                                                                data={'sale': self.sale_order_id.id,
                                                                                        'package': quant_package.id,
                                                                                        'barcode': self.id_barcode.name,
                                                                                        'group': roll_no})
                    
                elif self.label_type == 'sci_custom':
                    action = self.env.ref('inno_packaging.action_report_print_sci_custom_label',
                                        raise_if_not_found=False).report_action(docids=quant_package.id,
                                                                                data={'sale': self.sale_order_id.id,
                                                                                        'package': quant_package.id,
                                                                                        'barcode': self.id_barcode.name,
                                                                                        'group': roll_no})
                
                elif self.label_type == 'livabliss':
                    action = self.env.ref('inno_packaging.action_report_print_livabliss_label',
                                        raise_if_not_found=False).report_action(docids=quant_package.id,
                                                                                data={'sale': self.sale_order_id.id,
                                                                                        'package': quant_package.id,
                                                                                        'barcode': self.id_barcode.name,
                                                                                        'group': roll_no})
                elif self.label_type =='livabliss_upc':
                    action = self.env.ref('inno_packaging.action_report_print_livabliss_upc_label',
                                        raise_if_not_found=False).report_action(docids=quant_package.id,
                                                                                data={'sale': self.sale_order_id.id,
                                                                                        'package': quant_package.id,
                                                                                        'barcode': self.id_barcode.name,
                                                                                        'group': roll_no})
                return action
