from odoo import fields, models, _, api
from datetime import datetime
from odoo.exceptions import UserError, ValidationError, MissingError
import logging

_logger = logging.getLogger(__name__)


class Job_workLine(models.Model):
    _name = "jobwork.barcode.line"

    barcode_id = fields.Many2one("mrp.barcode", Barcode="Barcode", readonly="1")
    location_id = fields.Many2one(related="barcode_id.location_id")
    mrp_id = fields.Many2one(related="barcode_id.mrp_id", String="MMP ID")
    product_id = fields.Many2one(related="barcode_id.product_id", string="Product")
    inno_finishing_size_id = fields.Many2one(related="product_id.inno_finishing_size_id", string='Finishing Size')
    state = fields.Selection(
        [('draft', 'DRAFT'), ('accepted', 'Accepted'), ('rejected', 'REJECTED'), ('cancel', 'CANCEL'),
         ('received', 'RECEIVED')],
        string='Status', default='draft', tracking=True,)
    rate = fields.Float("Rate", readonly="1", store=True)
    finishing_work_id = fields.Many2one(comodel_name="finishing.work.order", readonly="1")
    date = fields.Datetime(string="Current Date", default=lambda *a: datetime.now(), readonly="1")
    rate_incentive_id = fields.Many2one("rate.and.incentive", string="Rate & Incentive")
    cancel_reason = fields.Text("Cancel Reason")
    total_area = fields.Float(string="Area", digits=(4, 4), store=True)
    unit = fields.Selection(
        [('sq_yard', 'Sq. Yard'), ('feet', 'Feet'), ('sq_feet', 'Sq. Feet'), ('choti', 'Choti'),
         ('sq_meter', 'Sq. Meter')],
        string='Units', tracking=True, readonly="1", store=True)

    currency_id = fields.Many2one(related='finishing_work_id.currency_id', store=True, string='Currency', readonly=True)
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', store=True)
    price_total = fields.Monetary(compute='_compute_amount', string='Total', store=True)
    price_tax = fields.Float(compute='_compute_amount', string='Tax', store=True)
    invoice_status = fields.Selection([
        ('no', 'Nothing to Bill'),
        ('invoiced', 'Fully Billed'),
    ], string='Billing Status', default='no',)
    cancel_penality = fields.Boolean()
    #
    # @api.depends('rate_incentive_id.rate', 'rate_incentive_id.is_size_wize', 'rate_incentive_id.size_wise_rate_line','state',)
    # def _compute_rate_area_and_units_finishing(self):
    #     for rec in self:
    #         rec.rate = 0.0
    #         if rec.rate_incentive_id.is_sample:
    #             if rec.rate_incentive_id.is_size_wize:
    #                 rec.write({'rate': rec.rate_incentive_id.size_wise_rate_line.filtered(lambda bl: bl.product_id.id in rec.product_id.ids)[0].rate})
    #             else:
    #                 rec.write({'rate': rec.rate_incentive_id.rate})
    #         else:
    #             line = rec.rate_incentive_id.size_wise_rate_line.filtered(lambda bl: rec.product_id.id in bl.product_id.ids)
    #             rec.write({'rate': line[0].rate if line else 0.00, 'total_area' : line[0].total_area if line else 0.00,'unit' : line[0].rate_incentive_id.unit if line else 'sq_yard'})

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
            quantity=self.total_area,
            price_subtotal=self.price_subtotal,
        )

    @api.depends('rate', 'total_area')
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

    def unlink(self):
        if self.finishing_work_id:
            self.barcode_id.finishing_jobwork_id = False
            self.barcode_id.current_process = False
            self.barcode_id.full_finishing = False
        return super(Job_workLine, self).unlink()
