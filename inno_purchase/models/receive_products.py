import base64
from odoo import fields, models, _, api
from odoo.exceptions import UserError
from datetime import timedelta
from dateutil import relativedelta
from datetime import datetime


class InnoReceiveProducts(models.Model):
    _name = "inno.receive"
    _description = 'Receive Products'
    _rec_name = "reference"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id DESC'

    READONLY_STATES = {
        'purchase': [('readonly', True)],
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    reference = fields.Char("Reference", default='/')
    subcontractor_id = fields.Many2one('res.partner', string='Vendor', tracking=True)
    receive_docs = fields.Char("Vendor Receive No")
    date = fields.Date(string='Date Issued', default=lambda *a: datetime.now(), )
    location = fields.Many2one("stock.location", string="Destination Location")
    inno_purchase_id = fields.Many2one("inno.purchase", string="Purchase No")
    inno_receive_line = fields.One2many("inno.receive.line", 'receive_id')
    state = fields.Selection([('draft', 'DRAFT'), ('ready', 'READY'), ('done', 'DONE'), ('locked', 'LOCKED'),
                              ('cancel', 'CANCELLED')], string='Status', default='draft', tracking=True)
    receive_invoice = fields.Char("Vendor Invoice No")
    receipt_no = fields.Char("Receipt Book No.")
    invoice_date = fields.Date(string='Invoice Date')

    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, states=READONLY_STATES,
                                 default=lambda self: self.env.company.id)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, states=READONLY_STATES,
                                  default=lambda self: self.env.company.currency_id.id)
    tax_totals = fields.Binary(compute='_compute_tax_totals', exportable=False)
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all')
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all',
                                     tracking=True)
    amount_total_words = fields.Char("Amount total in words", compute="_compute_amount_total_words")
    types = fields.Selection([('yarn', 'YARN'), ('wool', 'WOOL'), ('purchase', 'PURCHASE'),('tufting_cloth_weaving', 'TUFTING CLOTH WEAVING'),
         ('newar_production', 'NEWAR PRODUCTION'), ('tana_job_order', 'TANA JOB ORDER'),
         ('third_backing_cloth', 'THIRD BACKING CLOTH'), ('spinning', 'SPINNING')], string='Types', )
    inno_purchase_return_id = fields.Many2one("inno.purchase", string="Purchase No")
    parent_id = fields.Many2one("inno.receive", string="Receive No")
    return_id = fields.Many2one("inno.receive", string="Return No")
    received_by = fields.Many2one('res.partner', string='Received By', )
    supplier_date = fields.Date(string='Supplier Challan Date', )
    supplier_invoice_date = fields.Date(string='Supplier Invoice Date', )

    @api.depends('amount_total', 'currency_id')
    def _compute_amount_total_words(self):
        for record in self:
            record.amount_total_words = record.currency_id.amount_to_text(record.amount_total)

    @api.depends('inno_receive_line.price_total')
    def _amount_all(self):
        for order in self:
            order_lines = order.inno_receive_line

            if order.company_id.tax_calculation_rounding_method == 'round_globally':
                tax_results = self.env['account.tax']._compute_taxes([
                    line._convert_to_tax_base_line_dict()
                    for line in order_lines
                ])
                totals = tax_results['totals']
                amount_untaxed = totals.get(order.currency_id, {}).get('amount_untaxed', 0.0)
                amount_tax = totals.get(order.currency_id, {}).get('amount_tax', 0.0)
            else:
                amount_untaxed = sum(order_lines.mapped('price_subtotal'))
                amount_tax = sum(order_lines.mapped('price_tax'))

            order.amount_untaxed = amount_untaxed
            order.amount_tax = amount_tax
            order.amount_total = order.amount_untaxed + order.amount_tax

    @api.depends('inno_receive_line.tax_id', 'inno_receive_line.price_subtotal', 'amount_total', 'amount_untaxed')
    def _compute_tax_totals(self):
        for order in self:
            order_lines = order.inno_receive_line
            order.tax_totals = self.env['account.tax']._prepare_tax_totals(
                [x._convert_to_tax_base_line_dict() for x in order_lines],
                order.currency_id or order.company_id.currency_id,
            )

    def create_sequence(self):
        if self.reference == '/':
            self.write({'reference': self.env['ir.sequence'].next_by_code('po_rc_seq') or '/'})

    def open_receiving_form(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _(f"{self.reference}"),
            'view_mode': 'form',
            'res_model': 'inno.receive',
            'res_id': self.id
        }

    def open_vendor_bills(self):
        record = self.env['account.move'].search([('receive_id', '=', self.id)])
        action = {
            'name': "Bills",
            'view_mode': 'form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
        }
        if len(record) > 1:
            action.update({'view_mode': 'tree,form', 'domain': [('id', 'in', record.ids)]})
        else:
            action.update({'view_type': 'form', 'res_id': record[0].id})
        return action

    def open_main_receipt(self):
        record = self.env['stock.picking'].search([('receive_id', '=', self.id)])
        action = {
            'name': "Receipts",
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
        }
        if len(record) > 1:
            action.update({'view_mode': 'tree,form', 'domain': [('id', 'in', record.ids)]})
        else:
            action.update({'view_type': 'form', 'res_id': record[0].id})
        return action

    def button_confirm(self):
        if self._context.get('status') == 'draft':
            for rec in self.inno_receive_line:
                if rec.product_id:
                    if rec.receive_qty <= 0:
                        raise UserError(_("Product receive quantity is always greater than zero"))
                    if rec.invoice_qty <= 0:
                        raise UserError(_("Product invoice quantity is always greater than zero"))
                    if self.parent_id:
                        if rec.return_receive_qty <= 0:
                            raise UserError(_("Product return receive quantity is always greater than zero"))
                        if rec.return_invoice_qty <= 0:
                            raise UserError(_("Product return invoice quantity is always greater than zero"))
                self.state = 'ready'
        elif self._context.get('status') == 're_validate':
            operation_type = self.location.warehouse_id.in_type_id
            try:
                if self.parent_id:
                    picking_id = self.env['stock.picking'].search([('receive_id', '=', self.parent_id.id)], limit=1)
                    job_stock_move = self.prepare_job_stock_move()
                    pick_id = self.env['stock.picking'].sudo().create({
                        'name': self.location.warehouse_id.out_type_id.sequence_id.next_by_id(),
                        'partner_id': self.subcontractor_id.id,
                        'picking_type_id': self.location.warehouse_id.out_type_id.id,
                        'location_dest_id': self.env['stock.location'].search([('usage', '=', 'supplier')], limit=1).id,
                        'location_id': self.location.id,
                        'move_ids': job_stock_move,
                        'origin': _("Return of %s") % picking_id.name,
                        'inno_purchase_id': self.inno_purchase_id.id,
                        'receive_id': self.id,
                    })
                    pick_id.button_validate()
                    self.update_invoice_receive_qty()
                else:
                    job_stock_move = self.prepare_job_stock_move()
                    pick_id = self.env['stock.picking'].sudo().create({
                        'name': operation_type.sequence_id.next_by_id(),
                        'partner_id': self.subcontractor_id.id,
                        'picking_type_id': operation_type.id,
                        'location_dest_id': self.location.id,
                        'location_id': self.env['stock.location'].search([('usage', '=', 'supplier')], limit=1).id,
                        'move_ids': job_stock_move,
                        'origin': f"{self.reference}",
                        'inno_purchase_id': self.inno_purchase_id.id,
                        'receive_id': self.id,
                    })
                    lot_lines = self.inno_receive_line.filtered(lambda lt: lt.lot)
                    if lot_lines:
                        self.update_lot_no(pick_id, lot_lines)
                    pick_id.button_validate()
                    self.update_invoice_receive_qty()
            except Exception as ex:
                raise UserError(_(ex))
            self.state = 'done'
        elif self._context.get('status') == 'bill':
            if self.receive_invoice and self.receipt_no and self.invoice_date:
                try:
                    journal_id = self.env['inno.config'].sudo().search([], limit=1).purchase_journal_id
                    if not journal_id:
                        raise UserError(_("Please ask your admin to set purchase Journal"))
                    invoice_lines = self.prepare_invoice_lines(journal_id)
                    bill_id = self.env['account.move'].create({
                        'move_type': 'in_invoice',
                        'partner_id': self.subcontractor_id.id,
                        'date': fields.Datetime.now(),
                        'invoice_date': self.invoice_date,
                        'inno_purchase_id': self.inno_purchase_id.id,
                        'receive_id': self.id,
                        'invoice_line_ids': invoice_lines,
                        "receive_invoice": self.receive_invoice,
                        'journal_id': journal_id.id
                    })
                    amount = bill_id.tax_totals.get('amount_total')
                    round_amount = amount % 1
                    up_round_off = self.env['account.cash.rounding'].sudo().search([('name', '=', 'Round UP')])
                    dowm_round_off = self.env['account.cash.rounding'].sudo().search([('name', '=', 'Round Down')])
                    if round_amount > 0 and round_amount < 0.50:
                        bill_id.write({'invoice_cash_rounding_id': dowm_round_off.id})
                    elif round_amount > 0:
                        bill_id.write({'invoice_cash_rounding_id': up_round_off.id})
                    # bill_id.action_post()
                    self.state = 'locked'
                except Exception as ex:
                    raise UserError(_(ex))
            else:
                raise UserError(_("Add Vendor Invoice number,Receipt Book No and Invoice Date "))
        elif self._context.get('status') == 'return':
            new_receive = self.copy()
            new_receive.write({'parent_id': self.id, 'inno_purchase_return_id': self.inno_purchase_id.id})
            for line in self.inno_receive_line:
                new_line = line.copy()
                new_line.write({'receive_id': new_receive.id})
            new_receive.inno_purchase_id = False
            new_receive.write({'reference': self.env['ir.sequence'].next_by_code('po_return_seq') or '/'})
            self.write({'return_id': new_receive.id})
            return {
                'type': 'ir.actions.act_window',
                'name': "Return Products",
                'view_mode': 'form',
                'res_model': 'inno.receive',
                'res_id': new_receive.id
            }
        elif self._context.get('status') == 'credit_note':
            pass

    def prepare_invoice_lines(self, journal_id):
        tax_id = self.subcontractor_id.property_account_position_id.tax_ids.tax_dest_id
        invoice_lines = [(0, 0, {'display_type': 'line_section', 'name': 'Products'})]
        invoice_lines.extend([
            (0, 0,
             {'product_id': rec.product_id.id if rec.product_id else False, 'product_uom_id': rec.uom_id.id,
              'quantity': self.get_qty_for_invoice(rec),
              'price_unit': self.get_rate_for_invoice(rec),
              'name': rec.label if not rec.product_id else rec.product_id.name,
              'tax_ids': [(4, tx.id) for tx in rec.tax_id] if rec.tax_id else False, 'discount': rec.discount,
              'inno_price': rec.rate, 'remarks': rec.remarks,
              'account_id': journal_id.default_account_id.id}) for rec in self.inno_receive_line])
        return invoice_lines


    def get_qty_for_invoice(self,rec):
        if self.types in ['tufting_cloth_weaving', 'third_backing_cloth']:
            return float(rec.receive_qty)
        else:
            return float (rec.receive_qty if rec.deal_uom_id.id not in rec.uom_id.ids and rec.deal_uom_id else rec.invoice_qty)

    def get_rate_for_invoice(self, rec):
        if self.types in ['tufting_cloth_weaving','third_backing_cloth']:
            return round(rec.price_subtotal / rec.receive_qty,3)
        else:
            return round(float(rec.price_subtotal / rec.receive_qty if rec.deal_uom_id.id not in rec.uom_id.ids and rec.product_id and rec.deal_uom_id else rec.rate),2)

    def update_invoice_receive_qty(self):
        for rec in self.inno_receive_line:
            if self.parent_id:
                rec.purchase_line_id.return_invoice_qty += rec.return_invoice_qty
                rec.purchase_line_id.return_receive_qty += rec.return_receive_qty
            else:
                rec.purchase_line_id.invoice_qty += rec.invoice_qty
                rec.purchase_line_id.receive_qty += rec.receive_qty

    def prepare_job_stock_move(self, ):
        """
        Prepare the stock move line as per the component set in the selected operation
        """
        moves = []
        alloted_components = self.inno_receive_line
        moves.extend([(0, 0, {'name': f"Vendor",
                              'product_id': component.product_id.id,
                              'product_uom_qty': component.return_receive_qty if self.parent_id else component.receive_qty,
                              'quantity_done': component.return_receive_qty if self.parent_id else component.receive_qty,
                              'product_uom': component.uom_id.id,
                              'location_id': self.location.id if self.parent_id else self.env['stock.location'].search(
                                  [('usage', '=', 'supplier')],
                                  limit=1).id,
                              'location_dest_id': self.env['stock.location'].search([('usage', '=', 'supplier')],
                                                                                    limit=1).id if self.parent_id else self.location.id,
                              }) for component in alloted_components if component.product_id])
        return moves

    def update_lot_no(self, pick, lot_lines):
        for rec in lot_lines:
            rec.product_id.tracking = 'lot'
            move_line = pick.move_ids.filtered(lambda mv: mv.product_id == rec.product_id).move_line_ids[0]
            move_line.write({'lot_name': rec.lot})
            move_line.lot_id.write({'receive_line_id': rec.id})


class InnoReceiveProductsline(models.Model):
    _name = "inno.receive.line"
    _description = 'Receive Products Lines'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id DESC'

    product_id = fields.Many2one("product.product", string="Product")
    demand_qty = fields.Float("Demand Qty", digits=(12, 3))
    receive_qty = fields.Float("Receive", digits=(12, 3))
    invoice_qty = fields.Float("Invoice", digits=(12, 3))
    rate = fields.Float("Rate", digits=(12, 2))
    uom_id = fields.Many2one("uom.uom", string="Units", )
    receive_id = fields.Many2one("inno.receive")
    lot = fields.Char("Lot")
    remarks = fields.Text("Remarks")
    purchase_line_id = fields.Many2one("inno.purchase.line")
    tax_id = fields.Many2many("account.tax", string="Tax")
    label = fields.Char("Label")
    currency_id = fields.Many2one(related='receive_id.currency_id', store=True, string='Currency', readonly=True)
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Tax', store=True)
    deal_uom_id = fields.Many2one(related="purchase_line_id.deal_uom_id", string="Deal Units", )
    demand_deal_qty = fields.Float("Demand Deal Qty", digits=(12, 3))
    return_receive_qty = fields.Float("Return Receive", digits=(12, 3))
    return_invoice_qty = fields.Float("Return Invoice", digits=(12, 3))
    discount = fields.Float('Discount %')
    invoice_stock_qty = fields.Float("Stock Invoice", digits=(12, 3))
    weight_per_mtr = fields.Float("Weight/Meter",compute='_compute_avg_mtr', digits=(12, 3), store=True)
    machines = fields.Selection(
        [('Machine -1', 'Machine -1'), ('Machine -2', 'Machine -2'), ('Machine -3', 'Machine -3'),
         ('Machine -4', 'Machine -4'),
         ('Machine -5', 'Machine -5'), ('Machine -6', 'Machine -6'), ('Machine -7', 'Machine -7'),
         ('Machine -8', 'Machine -8'), ('Machine -9', 'Machine -9'), ('Machine -10', 'Machine -10')],
        string='Machine', )
    inno_machine_line = fields.One2many("inno.machine.records", 'receive_line_id')

    @api.depends('invoice_qty', 'receive_qty',)
    def _compute_avg_mtr(self):
        for rec in self:
            rec.weight_per_mtr = 0.00
            if rec.receive_id.types in ['tufting_cloth_weaving','third_backing_cloth'] and rec.invoice_qty >0.00 and rec.invoice_qty >0.00:
                rec.weight_per_mtr = round(rec.receive_qty/rec.invoice_qty,3)

    def _convert_to_tax_base_line_dict(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.receive_id.inno_purchase_id.subcontractor_id,
            currency=self.currency_id,
            product=self.product_id,
            taxes=self.tax_id,
            price_unit=self.rate - (self.rate * self.discount / 100) if self.discount else self.rate,
            quantity=self.return_invoice_qty if self.receive_id.parent_id else self.invoice_qty,
            price_subtotal=self.price_subtotal,
        )

    @api.depends('invoice_qty', 'rate', 'tax_id', 'return_invoice_qty')
    def _compute_amount(self):
        for line in self:
            tax_results = self.env['account.tax']._compute_taxes([line._convert_to_tax_base_line_dict()])
            totals = list(tax_results['totals'].values())[0]
            amount_untaxed = totals['amount_untaxed']
            amount_tax = totals['amount_tax']
            line.update({
                'price_subtotal': amount_untaxed,
                'price_tax': amount_tax,
                'price_total': amount_untaxed + amount_tax,
            })

    def button_for_machine_records(self):
        return {
            'type': 'ir.actions.act_window',
            'name': "Machines Records",
            'view_mode': 'form',
            'res_model': 'inno.receive.line',
            'res_id': self.id,
            'target' : 'new'
        }
class InnoMachineRecordsQty(models.Model):
    _name = "inno.machine.records"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id DESC'

    machines = fields.Selection(
        [('Machine -1', 'Machine -1'), ('Machine -2', 'Machine -2'), ('Machine -3', 'Machine -3'),
         ('Machine -4', 'Machine -4'),
         ('Machine -5', 'Machine -5'), ('Machine -6', 'Machine -6'), ('Machine -7', 'Machine -7'),
         ('Machine -8', 'Machine -8'), ('Machine -9', 'Machine -9'), ('Machine -10', 'Machine -10')],
        string='Machine', )
    receive_qty = fields.Float("Receive", digits=(12, 3))
    invoice_qty = fields.Float("Invoice", digits=(12, 3))
    weight_per_mtr = fields.Float("Weight/Meter", compute='_compute_avg_mtr', digits=(12, 3), store=True)
    receive_line_id = fields.Many2one("inno.receive.line")

    @api.depends('invoice_qty', 'receive_qty',)
    def _compute_avg_mtr(self):
        for rec in self:
            rec.weight_per_mtr = 0.00
            if rec.receive_line_id.receive_id.types in ['tufting_cloth_weaving','third_backing_cloth'] and rec.invoice_qty >0.00 and rec.invoice_qty >0.00:
                rec.weight_per_mtr = round(rec.receive_qty/rec.invoice_qty,3)
                rec.receive_line_id.receive_qty += rec.receive_qty
                rec.receive_line_id.invoice_qty += rec.invoice_qty
                rec.receive_line_id._compute_avg_mtr()