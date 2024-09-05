from odoo import fields, models, _, api
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)


class RateAndIncentive(models.Model):
    _name = "rate.and.incentive"

    product_tmpl_id = fields.Many2one(comodel_name="product.template", string="Design")
    rate = fields.Float(string="Rate", digits=(4, 2))
    rate_discount = fields.Float(string="Rate Discount", digits=(3, 2))
    sample_rate = fields.Float(string="Sample Rate", digits=(4, 2))
    fixed_incentive = fields.Float(string="Fixed Incentive", digits=(3, 2))
    expire_incentive = fields.Float(string="Expirable Incentive", digits=(3, 2))
    qty = fields.Integer("Quantity",)
    finishing_work_id = fields.Many2one(comodel_name="finishing.work.order", readonly="1")
    original_rate = fields.Float()
    is_sample = fields.Boolean()
    total_area = fields.Float(string="Area",digits=(4, 4))
    unit = fields.Selection(
        [('sq_yard', 'Sq. Yard'), ('feet', 'Feet'), ('sq_feet', 'Sq. Feet'), ('choti', 'Choti'),
         ('sq_meter', 'Sq. Meter')],
        string='Units', tracking=True, readonly="1",store=True)
    size_wise_rate_line = fields.One2many(comodel_name="size.wise.rate", inverse_name='rate_incentive_id',
                                          string="Size Wize")
    is_size_wize = fields.Boolean("Size Wize")
    status = fields.Selection(related="finishing_work_id.status")
    def update_rate(self):
        if not self.is_sample:
            raise UserError(_("only sample rate can be updated."))
        return {
            'name': "Update Sample Rate",
            'view_mode': 'form',
            'res_model': 'inno.sample.rate.update',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'from_finishing': True}
        }

    def update_size_wize_rate(self):
        size_wise_rates = self.env['rate.and.incentive'].search([('id', '=', self.id)])
        action= {
            'name': "Size Wize Rate",
            'view_mode': 'form',
            'res_model': 'rate.and.incentive',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'from_finishing': True}
        }
        if size_wise_rates:
            action.update({'view_type': 'form', 'res_id': size_wise_rates.id})
        return action


class Size_wize_rate(models.Model):
    _name = "size.wise.rate"

    product_tmpl_id = fields.Many2one(comodel_name="product.template", string="Design")
    size_id = fields.Many2one(comodel_name="inno.size", string="Size")
    rate = fields.Float(string="Rate", digits=(4, 2))
    rate_incentive_id = fields.Many2one("rate.and.incentive", string="Rate & Incentive")
    product_id = fields.Many2one(comodel_name="product.product", string="Product")
    total_area = fields.Float(string="Area", digits=(4, 4))




class Incentive(models.Model):
    _inherit = "inno.incentive.penalty"

    type = fields.Selection(
        selection_add=[('expire_incentive', 'Expirable Incentive'), ('finishing_incentive', 'Finishing Incentive')]
    )
