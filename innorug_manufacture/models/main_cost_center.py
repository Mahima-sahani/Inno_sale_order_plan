import datetime
from odoo import fields, models, _, api
from datetime import date
from odoo.exceptions import UserError
import logging
_logger = logging.getLogger(__name__)


class MainCostCenter(models.Model):
    _name = "main.costcenter"
    _description = 'Main Cost center'
    _rec_name = "reference"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    reference = fields.Char(string="Reference")
    main_job_work_id = fields.Many2one(comodel_name="main.jobwork", string="Job Work")
    subcontractor_id = fields.Many2one(related="main_job_work_id.subcontractor_id", string="Subcontractor")
    issue_date = fields.Date(related="main_job_work_id.issue_date", string='Issued Date')
    expected_received_date = fields.Date(string='Expected Received Date')
    division_id = fields.Many2one(related="main_job_work_id.division_id", store=True, string='Division')

    @api.model
    def create(self, vals):
        if vals.get('MainCostCenter', _('New')) == _('New'):
            vals['reference'] = self.env['ir.sequence'].next_by_code(
                'main.costcenter') or _('New')
        res = super(MainCostCenter, self).create(vals)
        return res

    def generate_bill(self):
        invoice_lines = self.prepare_invoice_lines()
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.subcontractor_id.id,
            'date': datetime.datetime.today(),
            'invoice_date': datetime.datetime.today(),
            'main_cost_center_id': self.id,
            'invoice_line_ids': invoice_lines
        })

    def prepare_invoice_lines(self):
        invoice_lines = [(0, 0, {'display_type': 'line_section', 'name': 'Products'})]
        invoice_lines.extend([(0, 0, {
            'product_id': line.product_id.id,
            'quantity': line.receive_sqr_area,
            'price_unit': line.product_id.standard_price,
        }) for line in self.cost_center_ids])
        received_barcodes = self.cost_center_ids.job_work_id.barcodes.filtered(lambda bcode: bcode.state == '5_verified')
        late_penalty = sum(received_barcodes.mapped('penalty'))
        lost_penalty = sum(received_barcodes.mapped('lost_penalty'))
        if late_penalty or lost_penalty:
            invoice_lines.append((0, 0, {'display_type': 'line_section', 'name': 'Penalties'}))
        if late_penalty:
            penalty_product = self.env['product.product'].search([('default_code', '=', 'WEAVPENALTY')])
            invoice_lines.append((0, 0, {
                'product_id': penalty_product.id,
                'quantity': 1,
                'price_unit': -late_penalty}))
        if lost_penalty:
            penalty_product = self.env['product.product'].search([('default_code', '=', 'LOSTPENALTY')])
            invoice_lines.append((0, 0, {
                'product_id': penalty_product.id,
                'quantity': 1,
                'price_unit': -lost_penalty}))
        return invoice_lines



