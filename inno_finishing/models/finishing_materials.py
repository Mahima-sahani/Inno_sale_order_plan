from odoo import models, fields, api


class Materials(models.Model):
    _name = 'finishing.materials'

    product_id = fields.Many2one(comodel_name ="product.product", string="Components")
    product_qty = fields.Float("Quantity", digits=(12, 4))
    uom_id = fields.Many2one(related="product_id.uom_id", string="Units",)
    finishing_work_id = fields.Many2one(comodel_name="finishing.work.order", string="Finishing")
    location_id = fields.Many2one("stock.location", string="Location", default=lambda self: self.env.user.material_location_id.id,domain=[('usage', '=', 'internal')])
    rate = fields.Float(string="Rate", digits=(4, 2))
    qty_released = fields.Float("Released", digits=(12, 4))
    qty_amended = fields.Float("Amended", digits=(12, 4))
    qty_return = fields.Float("Return", digits=(12, 4))
    qty_previous = fields.Float("Previous", digits=(12, 4))
    extra = fields.Boolean("If Extra")
    currency_id = fields.Many2one(related='finishing_work_id.currency_id', store=True, string='Currency', readonly=True)
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Tax', store=True)
    qty_retained = fields.Float("Retained", digits=(12, 4))
    closed = fields.Boolean("Closed")
    remark = fields.Text("Remarks")
    added_in_bill = fields.Boolean()


    def _convert_to_tax_base_line_dict(self):
        """ Convert the current record to a dictionary in order to use the generic taxes computation method
        defined on account.tax.

        :return: A python dictionary.
        """
        self.ensure_one()
        return self.env['account.tax']._convert_to_tax_base_line_dict(
            self,
            partner=self.finishing_work_id.subcontractor_id,
            currency=self.currency_id,
            product=self.product_id,
            taxes=False,
            price_unit=self.rate,
            quantity=self.qty_amended - self.qty_return-self.qty_retained if self.extra else self.qty_released - self.qty_return,
            price_subtotal=self.price_subtotal,
        )

    @api.depends('rate', 'qty_amended','qty_released','qty_return','extra')
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