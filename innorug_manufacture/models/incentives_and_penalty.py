from odoo import models, fields


class IncentivePenalty(models.Model):
    _name = 'inno.incentive.penalty'
    _description = 'Records all the incentives and penalty records'

    type = fields.Selection(selection=[('time_penalty', 'Time Penalty'), ('bazaar_penalty', 'Bazaar Limit Exceeded'),
                                       ('qa_penalty', 'QC Penalty'), ('incentive', 'Bazaar Incentive'),
                                       ('time_incentive', 'Time Incentive'), ('re_printing', 'Barcode Re-Print'),
                                       ('cancel', 'Cancellation Penalty'), ('retention', 'Retention')])
    record_date = fields.Datetime()
    amount = fields.Float()
    barcode_id = fields.Many2one(comodel_name='mrp.barcode')
    workcenter_id = fields.Many2one(comodel_name='mrp.workorder', string='Work Order')
    remark = fields.Text()
    model_id = fields.Many2one(comodel_name='ir.model')
    rec_id = fields.Integer()
    partner_id = fields.Many2one(comodel_name='res.partner', string='Subcontractor')
    due_cleared = fields.Boolean(help='This field is only used for subcontractor direct penalty.')
