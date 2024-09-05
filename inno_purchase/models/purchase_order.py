from odoo import fields, models, _, api
import logging
import base64
import logging

_logger = logging.getLogger(__name__)


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    inno_purchase_id = fields.Many2one("inno.purchase")
    remark = fields.Char("Remark")
    is_sale = fields.Boolean(compute='_compute_is_sale')
    order_type = fields.Selection(
        [('spinning', 'Spinning'), ('cloth', 'Cloth'), ('carpet', 'Carpet'), ('other', 'Other Order')],
        string='Order', )
    planing_ids = fields.Many2many(comodel_name="inno.sale.order.planning", string="Plan NOs.")

    def upload_Planning_Product(self):
        if self.planing_ids:
            record = self.planing_ids
            raw_material_group = ['acrlicy_yarn', 'polyster_yarn', 'jute_yarn', 'cotton_cone', 'silk', 'lefa', 'nylon',
                                  'woolen_yarn', 'cotton_yarn', 'yarn']
            products = record.sale_order_id.mrp_production_ids.move_raw_ids.product_id
            attribute_id = self.env['product.attribute'].search([('name', '=', 'SHADE')], limit=1)
            attribute_value = self.env['product.attribute.value'].search(
                [('attribute_id', '=', attribute_id.id), ('name', '=', 'NO Shade')], limit=1)
            for rec in products:
                if rec.product_tmpl_id.raw_material_group not in raw_material_group:
                    continue
                if rec.product_tmpl_id.with_shade:
                    self.update_or_create_po_line(rec)
                else:
                    sku = rec.product_tmpl_id.product_variant_ids.filtered(
                        lambda pv: attribute_value.name in pv.product_template_attribute_value_ids.mapped('name'))
                    if not sku:
                        rec.product_tmpl_id.attribute_line_ids.filtered(
                            lambda al: al.attribute_id.id == attribute_id.id).write(
                            {'value_ids': [(4, attribute_value.id)]})
                        sku = rec.product_tmpl_id.product_variant_ids.filtered(
                            lambda pv: attribute_value.name in pv.product_template_attribute_value_ids.mapped(
                                'name'))
                    if sku:
                        self.update_or_create_po_line(sku, rec,True)

    def update_or_create_po_line(self, product_id, actual_product=False, no_shade=False):
        record = self.planing_ids
        order_line = self.order_line.filtered(lambda pv: pv.product_id.id == product_id.id)
        if no_shade:
            qty = round(sum(record.sale_order_id.mrp_production_ids.move_raw_ids.filtered(
                lambda mv: mv.product_id.id == actual_product.id).mapped('product_uom_qty')), 3)
        else:
            qty = round(sum(record.sale_order_id.mrp_production_ids.move_raw_ids.filtered(
                lambda mv: mv.product_id.id == product_id.id).mapped('product_uom_qty')), 3)
        if order_line:
            order_line.write({'product_qty': order_line.product_qty + qty})
        else:
            data = (0, 0, {'product_id': product_id.id,
                           'name': product_id.default_code if product_id.default_code else
                           f"{product_id.name} {product_id.product_template_variant_value_ids.name}",
                           'price_unit': 10, 'product_qty': qty})
            self.write({'order_line': [data]})

    def _compute_is_sale(self):
        for rec in self:
            rec.is_sale = True if rec._get_sale_orders() else False

    @api.model_create_multi
    def create(self, vals_list):
        orders = self.browse()
        partner_vals_list = []
        for vals in vals_list:
            company_id = vals.get('company_id', self.default_get(['company_id'])['company_id'])
            # Ensures default picking type and currency are taken from the right company.
            self_comp = self.with_company(company_id)
            if vals.get('name', 'New') == 'New':
                seq_date = None
                if vals.get('order_type') == 'spinning':
                    if 'date_order' in vals:
                        seq_date = fields.Datetime.context_timestamp(self,
                                                                     fields.Datetime.to_datetime(vals['date_order']))
                    vals['name'] = self_comp.env['ir.sequence'].next_by_code('po_spinning_seq',
                                                                             sequence_date=seq_date) or '/'
                elif vals.get('order_type') == 'cloth':
                    if 'date_order' in vals:
                        seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(
                            vals['date_order']))
                    vals['name'] = self_comp.env['ir.sequence'].next_by_code('po_cloth_seq',
                                                                             sequence_date=seq_date) or '/'
                elif vals.get('order_type') == 'other':
                    if 'date_order' in vals:
                        seq_date = fields.Datetime.context_timestamp(self, fields.Datetime.to_datetime(
                            vals['date_order']))
                    vals['name'] = self_comp.env['ir.sequence'].next_by_code('po_other_seq',
                                                                             sequence_date=seq_date) or '/'
                else:
                    vals['name'] = self_comp.env['ir.sequence'].next_by_code('purchase.order',
                                                                             sequence_date=seq_date) or '/'
            vals, partner_vals = self._write_partner_values(vals)
            partner_vals_list.append(partner_vals)
            orders |= super(PurchaseOrder, self_comp).create(vals)
        for order, partner_vals in zip(orders, partner_vals_list):
            if partner_vals:
                order.sudo().write(partner_vals)  # Because the purchase user doesn't have write on `res.partner`
        return orders

    def button_confirm(self):
        res = super(PurchaseOrder, self).button_confirm()
        if self._get_sale_orders().ids:
            self.carpet_print_pdf()
        return res

    def carpet_print_pdf(self):
        report = self.carpet_purchase_report()
        pdf = base64.b64encode(report).decode()
        if report:
            attachment = self.env['ir.attachment'].create({
                'name': 'Carpet_Purchase_Order_Report.pdf',
                'type': 'binary',
                'datas': pdf,
                'res_model': self._name,
                'res_id': self.id,
            })
            self.message_post(
                body="Purchase order report generated",
                attachment_ids=[attachment.id]
            )

    def action_create_invoice(self):
        res = super(PurchaseOrder, self).action_create_invoice()
        if res:
            invoice_id = res.get('res_id')
            invoice_obj = self.env['account.move'].search([('id','=',invoice_id)])
            for move_line in invoice_obj.invoice_line_ids:
                if move_line.purchase_line_id.total_area:
                    area = float(move_line.purchase_line_id.total_area)/float(move_line.purchase_line_id.product_qty)
                    inno_area = area*move_line.quantity
                    move_line.write({'inno_area':inno_area})
                if move_line.purchase_line_id.purchase_rate:
                    move_line.write({'inno_price':float(move_line.purchase_line_id.purchase_rate)})

    def carpet_purchase_report(self):
        report = \
            self.env.ref('inno_purchase.action_carpet_purchase_order',
                         raise_if_not_found=False).sudo()._render_qweb_pdf(
                'inno_purchase.action_carpet_purchase_order', res_ids=self.id)[0]
        return report

    def fetch_rate(self):
        for rec in self.order_line:
            supplier = self.env['inno.product.supplierinfo'].search(
                [('partner_id', '=', self.partner_id.id),
                 ('product_tmpl_id', '=', rec.product_id.product_tmpl_id.id)])
            supplier.update_rate()
            for supplier_info in supplier.variant_seller_ids:
                if int(rec.product_id.id) == int(supplier_info.product_id.id):
                    if supplier_info.product_id:
                        rec.write({'price_unit': supplier_info.price, 'purchase_rate': round(float(supplier_info.inno_supplierinfo_id.rate),3)})
                    else:
                        supplier.unlink()
                    break


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    total_invoice_qty = fields.Float("Invoice Qty")
    remark = fields.Char("Remark")
    total_area = fields.Char(string="Total Area", compute="_compute_total_area")
    deal_unit = fields.Char(string="Deal Unit")
    purchase_rate = fields.Float(string="Rate", digits=(10, 3))

    @api.onchange('purchase_rate')
    def onchange_purchase_rate(self):
        try:
            self.price_unit = (self.purchase_rate * float(self.total_area)) / self.product_qty
        except Exception as ex:
            pass

    @api.depends('product_qty', 'price_unit')
    def _compute_total_area(self):
        try:
            for rec in self:
                if rec.product_id and rec.product_qty:
                    rec.total_area = 0
                    size = rec.product_id.product_template_variant_value_ids.name
                    supplier = self.env['inno.product.supplierinfo'].search([('product_tmpl_id', '=', rec.product_id.product_tmpl_id.id)], limit=1)
                    area = self.env['inno.size'].search([('name', '=', size)])
                    if supplier:
                        if supplier.uom_id.name == 'm²':
                            if area.area_cm >0.0:
                                rec.total_area = area.area_cm * rec.product_qty
                            else:
                                rec.total_area = area.area_sq_mt * rec.product_qty
                            rec.write({'deal_unit': 'm²'})
                        elif supplier.uom_id.name == 'ft²':
                            rec.total_area = round(area.area * rec.product_qty,3)
                            rec.write({'deal_unit': 'ft²'})
                        elif supplier.uom_id.name == 'Sq. Yard':
                            rec.total_area = round(area.area_sq_yard * rec.product_qty,3)
                            rec.write({'deal_unit': 'Sq. Yard'})
                        rec.order_id.write({'order_type': 'carpet'})
                else:
                    rec.total_area = 0
        except Exception as e:
            _logger.info(f"=========EEEEEEEE============{e}")
