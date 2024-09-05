import base64
from odoo import fields, models, _, api
from odoo.exceptions import UserError
from datetime import timedelta
from dateutil import relativedelta


class InnoPurchaseLine(models.Model):
    _name = "inno.purchase.line"
    _description = 'Materials Details'

    READONLY_STATES = {
        'purchase': [('readonly', True)],
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    product_id = fields.Many2one("product.product", string="Product")
    available_qty = fields.Float("On-Hand Qty", related="product_id.qty_available", digits=(12, 4))
    product_qty = fields.Float("Qty", digits=(12, 3))
    uom_id = fields.Many2one(related="product_id.uom_id", string="Units", )
    rate = fields.Float("Rate", digits=(12, 2))
    inno_purchase_id = fields.Many2one("inno.purchase")
    lot = fields.Char("Lot")
    remarks = fields.Text("Remarks")
    receive_qty = fields.Float("Receive Qty", digits=(12, 3))
    invoice_qty = fields.Float("Invoice Qty", digits=(12, 3))
    tax_id = fields.Many2many("account.tax")
    currency_id = fields.Many2one(related='inno_purchase_id.currency_id', store=True, string='Currency', readonly=True)
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Tax', store=True)
    deal_uom_id = fields.Many2one("uom.uom", string="Deal Units", )
    deal_qty = fields.Float("Deal Qty", digits=(12, 3))
    return_receive_qty = fields.Float("Return Receive", digits=(12, 3))
    return_invoice_qty = fields.Float("Return Invoice", digits=(12, 3))
    discount = fields.Float('Discount %', )

    def _compute_amount(self):
        pass

    @api.onchange('product_id')
    def compute_tax_id(self):
        if self.product_id:
            for line in self:
                line = line.with_company(line.inno_purchase_id.company_id)
                fpos = line.inno_purchase_id.fiscal_position_id or line.inno_purchase_id.fiscal_position_id._get_fiscal_position(
                    line.inno_purchase_id.subcontractor_id)
                # filter taxes by company
                taxes = line.product_id.supplier_taxes_id.filtered(lambda r: r.company_id == line.env.company)
                line.tax_id = fpos.map_tax(taxes)

    def _convert_to_tax_base_line_dict(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.inno_purchase_id.subcontractor_id,
            currency=self.inno_purchase_id.currency_id,
            product=self.product_id,
            taxes=self.tax_id,
            price_unit=self.rate - (self.rate * self.discount / 100) if self.discount else self.rate,
            quantity=self.deal_qty if self.inno_purchase_id.types in ['purchase', 'tufting_cloth_weaving',
                                                                      'third_backing_cloth'] else self.product_qty,
            price_subtotal=self.price_subtotal,
        )

    @api.depends('product_qty', 'rate', 'tax_id', 'discount')
    def _compute_amount(self):
        for line in self:
            # line.price_subtotal = line.product_qty * line.rate
            tax_results = self.env['account.tax']._compute_taxes([line._convert_to_tax_base_line_dict()])
            totals = list(tax_results['totals'].values())[0]
            amount_untaxed = totals['amount_untaxed']
            amount_tax = totals['amount_tax']
            line.update({
                'price_subtotal': amount_untaxed,
                'price_tax': amount_tax,
                'price_total': amount_untaxed + amount_tax,
            })
