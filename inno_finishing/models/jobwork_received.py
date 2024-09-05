from odoo import fields, models, api, _
from odoo.exceptions import UserError
from datetime import datetime


class JobWorkReceived(models.Model):
    _name = 'jobwork.received'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "barcode_id"

    barcode_id = fields.Many2one(related="work_order_line_id.barcode_id", string="Barcode")
    finishing_work_id = fields.Many2one(related="work_order_line_id.finishing_work_id", string="Finish")
    baazar_id = fields.Many2one('finishing.baazar', string='Finishing')
    product_id = fields.Many2one(related="barcode_id.product_id", string="Product")
    inno_finishing_size_id = fields.Many2one(related="product_id.inno_finishing_size_id", string='Finishing Size')
    rate = fields.Float("Rate(INR)", related="work_order_line_id.rate")
    state = fields.Selection(
        [('draft', 'DRAFT'), ('received', 'RECEIVED'), ('verified', 'VERIFIED'), ('reject', 'Rejected')],
        string='Status')
    date = fields.Date(string="Current Date", default=lambda *a: datetime.now())
    penalty = fields.Float(string="Penalty(INR)")
    remark = fields.Char()
    operation_id = fields.Many2one(comodel_name='mrp.workcenter')
    is_full_finishing = fields.Boolean(related="barcode_id.full_finishing")
    incentive = fields.Float("Incentive(INR)")
    division_id = fields.Many2one(related='baazar_id.division_id')
    fixed_incentive = fields.Float("Fixed Incentive", related="work_order_line_id.rate_incentive_id.fixed_incentive")
    current_operation = fields.Many2one(comodel_name='mrp.workcenter', related="finishing_work_id.operation_id")
    work_order_line_id = fields.Many2one("jobwork.barcode.line")
    sample_rate = fields.Float("Sample Rate", related="work_order_line_id.rate_incentive_id.sample_rate")
    is_next_operation = fields.Boolean(compute="check_letexing_with_pattimurai", )
    total_area = fields.Float(string="Area", related="work_order_line_id.total_area")
    unit = fields.Selection(
        [('sq_yard', 'Sq. Yard'), ('feet', 'Feet'), ('sq_feet', 'Sq. Feet'), ('choti', 'Choti'),
         ('sq_meter', 'Sq. Meter')],
        string='Units', related="work_order_line_id.unit")
    invoice_status = fields.Selection([
        ('no', 'Nothing to Bill'),
        ('invoiced', 'Fully Billed'),
    ], string='Billing Status', default='no',related="work_order_line_id.invoice_status")
    space= fields.Char('    ', readonly=True)

    def check_letexing_with_pattimurai(self):
        config_id = self.env["inno.config"].sudo().search([], limit=1)
        for rec in self:
            if config_id.letexing_id == rec.finishing_work_id.operation_id and rec.finishing_work_id.is_external:
                rec.is_next_operation = True
            elif rec.is_full_finishing:
                rec.is_next_operation = True
            else:
                rec.is_next_operation = False

    @api.onchange('operation_id')
    def onchange_operation(self):
        wo = self.barcode_id.mrp_id.workorder_ids.filtered(lambda wo: self.operation_id.id in wo.workcenter_id.ids)
        if not wo:
            raise UserError(_("This operation cannot be assigned!"))

    def do_pass_or_reject(self):
        jobwork_barcode_id = self.env['jobwork.barcode.line'].sudo().search([
            ('finishing_work_id', '=', self.finishing_work_id.id), ('barcode_id', '=', self.barcode_id.id),
        ], limit=1)
        config_record = self.env['inno.config'].sudo().search([], limit=1)
        wo = self.barcode_id.mrp_id.sudo().workorder_ids.filtered(
            lambda wo: self.operation_id.id in wo.workcenter_id.ids)
        work_order = jobwork_barcode_id.mrp_id.workorder_ids.filtered(
            lambda wo: config_record.weaving_operation_id.id not in wo.workcenter_id.ids)
        self.state = self._context.get('status')
        washing_id = self.barcode_id.process_finished.filtered(
            lambda wo: config_record.washing_id.id in wo.workcenter_id.ids)
        if self._context.get('status') == 'verified':
            if (self.penalty or self.incentive) and not self.remark:
                raise UserError(_("Please Add remark for the penalty or the incentive you have added to this barcode."))
            if self.penalty:
                type = "qa_penalty"
                remark = "QA Penalty"
                self.update_penality_and_incentive(type, jobwork_barcode_id, config_record, self.penalty, wo, remark)
            if self.incentive:
                type = "finishing_incentive"
                remark = 'Qc Incentive'
                self.update_penality_and_incentive(type, jobwork_barcode_id, config_record, self.incentive, wo, remark)
            if self.operation_id:
                if self.barcode_id.full_finishing == True:
                    self.barcode_id.write({'state': '7_finishing', 'current_process': False, 'next_process': wo.id})
                else:
                    self.barcode_id.write({'state': '7_finishing', 'current_process': False, 'next_process': wo.id})
            if jobwork_barcode_id and self.finishing_work_id.operation_id == config_record.full_finishing_id:
                for rec in work_order:
                    jobwork_barcode_id.state = 'accepted'
                    self.barcode_id.sudo().write({'finishing_jobwork_id': False, 'location_id': self.baazar_id.sudo().location_id.id})
                    if not self.operation_id:
                        if rec == washing_id:
                            continue
                        else:
                            rec.finished_qty += 1
                        self.barcode_id.sudo().write({'current_process': False, 'next_process': False, 'state': '8_done', })
                        self.barcode_id.sudo().move_barcode_inventory()
            else:
                if self.barcode_id.full_finishing == True and self.operation_id != config_record.full_finishing_id:
                    for rec in work_order:
                        jobwork_barcode_id.state = 'accepted'
                        self.barcode_id.write({'finishing_jobwork_id': False, 'current_process': False,
                                               'location_id': self.baazar_id.location_id.id})
                        if not self.operation_id:
                            self.barcode_id.move_barcode_inventory()
                            if rec == washing_id:
                                continue
                            else:
                                rec.finished_qty += 1
                            self.barcode_id.write({'state': '8_done', 'next_process': False, })
                elif config_record.letexing_id == self.finishing_work_id.operation_id and self.finishing_work_id.is_external and not self.operation_id:
                    latex_id = self.barcode_id.mrp_id.workorder_ids.filtered(
                        lambda wo: config_record.letexing_id.id in wo.workcenter_id.ids)
                    patti_mr_id = self.barcode_id.mrp_id.workorder_ids.filtered(
                        lambda wo: 'Patti Murai' in wo.workcenter_id.mapped('name'))
                    if patti_mr_id:
                        latex_id.sudo().finished_qty += 1
                        patti_mr_id.sudo().finished_qty += 1
                        self.update_barcode_detailsa(jobwork_barcode_id)
                        self.barcode_id.write(
                            {'state': '7_finishing', 'process_finished': [(4, patti_mr_id.id), (4, latex_id.id)],
                             'next_process': self.env['mrp.workorder'].sudo().search(
                                 [('parent_id', '=', patti_mr_id.id)]).id})
                        if not self.barcode_id.next_process:
                            self.barcode_id.write({'state': '8_done', })
                            self.barcode_id.move_barcode_inventory()
                    else:
                        latex_id.sudo().finished_qty += 1
                        self.update_barcode_detailsa(jobwork_barcode_id)
                        self.barcode_id.write(
                            {'state': '7_finishing', 'process_finished': [(4, latex_id.id)],
                             'next_process': self.env['mrp.workorder'].sudo().search(
                                 [('parent_id', '=', latex_id.id)]).id})
                        if not self.barcode_id.next_process:
                            self.barcode_id.write({'state': '8_done', })
                            self.barcode_id.move_barcode_inventory()
                else:
                    if self.finishing_work_id.operation_id:
                        work_order = self.barcode_id.mrp_id.workorder_ids.filtered(
                            lambda wo: self.finishing_work_id.operation_id.id in wo.workcenter_id.ids)
                        if wo.id == work_order.id:
                            self.update_barcode_detailsa(jobwork_barcode_id)
                            if len(self.barcode_id.process_finished) == 1:
                                self.barcode_id.state = '5_verified'
                        else:
                            for rec in work_order:
                                rec.sudo().finished_qty += 1
                            self.update_barcode_detailsa(jobwork_barcode_id)
                            self.barcode_id.write({'process_finished': [(4, work_order.id)]})
                            self.barcode_id.write({'state': '7_finishing',
                                                   'next_process': self.env['mrp.workorder'].sudo().search(
                                                       [('parent_id', '=', work_order.id)]).id})
                            if not self.barcode_id.next_process:
                                self.barcode_id.state = '8_done'
                                self.barcode_id.move_barcode_inventory()
            rate_list = self.finishing_work_id.sudo().rate_incentive_ids.filtered(lambda
                                                                               rt: rt.fixed_incentive > 0 and
                                                                                   self.barcode_id.product_id.product_tmpl_id.id in
                                                                                   rt.product_tmpl_id.ids and self.state == 'verified')
            if rate_list:
                type = "finishing_incentive"
                remark = 'Fixed Incentive'
                self.fixed_incentive = rate_list.fixed_incentive * self.total_area
                self.update_penality_and_incentive(type, jobwork_barcode_id, config_record, self.fixed_incentive,
                                                   wo, remark)
            self.add_time_incentive_and_expirable_incentive()
        else:
            if self._context.get('status') == 'reject':
                self.state = 'reject'
                jobwork_barcode_id.state = 'rejected'
        self.check_and_verify_bazaar()

    def add_time_incentive_and_expirable_incentive(self):
        jobwork_barcodes_lines = self.finishing_work_id.sudo().jobwork_barcode_lines.filtered(
            lambda rec: rec.state in ["draft", "rejected", 'received'])
        if self.finishing_work_id.expected_date >= self.baazar_id.date and not jobwork_barcodes_lines:
            vals = {'rec_id': self.finishing_work_id.id,
                    'partner_id': self.finishing_work_id.subcontractor_id.id,
                    'model_id': self.env.ref('inno_finishing.model_finishing_work_order').id,
                    "remark": f"{self.finishing_work_id.name}", 'record_date': self.date, }
            amt = 0.0
            if self.finishing_work_id.time_incentive:
                total_time_incentive = self.finishing_work_id.time_incentive * sum(
                    self.finishing_work_id.jobwork_barcode_lines.mapped("total_area"))
                if total_time_incentive >0:
                    vals.update({'type': 'time_incentive', "amount": total_time_incentive})
                    amt = total_time_incentive
            rate_list = self.finishing_work_id.rate_incentive_ids.filtered(lambda rt: rt.expire_incentive > 0)
            if rate_list:
                sum_expire_amount = 0
                for rec in self.finishing_work_id.rate_incentive_ids:
                    if rec.expire_incentive > 0:
                        sum_exp = rec.expire_incentive * sum(
                            self.finishing_work_id.jobwork_barcode_lines.filtered(lambda pd: rec.product_tmpl_id.id
                                                                                             in pd.product_id.product_tmpl_id.ids).mapped(
                                'total_area'))
                        sum_expire_amount += sum_exp
                if sum_expire_amount:
                    vals.update({'type': 'expire_incentive', "amount": sum_expire_amount})
                    amt = sum_expire_amount
            if vals and amt > 0:
                self.env['inno.incentive.penalty'].create(vals)

    def check_and_verify_bazaar(self):
        bz_lines = self.baazar_id.sudo().jobwork_received_ids
        if bz_lines.filtered(lambda bl: bl.state == 'received'):
            return
        elif bz_lines.filtered(lambda bl: bl.state == 'reject'):
            return
        else:
            self.baazar_id.sudo().state = 'bill'

    def update_barcode_detailsa(self, jobwork_barcode_id):
        self.barcode_id.current_process = False
        jobwork_barcode_id.state = 'accepted'
        self.barcode_id.finishing_jobwork_id = False
        self.barcode_id.location_id = self.baazar_id.location_id.id

    def update_penality_and_incentive(self, type, jobwork_barcode_id, config_record, amount, wo, remark):
        vals = {'barcode_id': self.barcode_id.id,
                'rec_id': self.finishing_work_id.id,
                'model_id': self.env.ref('inno_finishing.model_finishing_work_order').id,
                'type': type, 'amount': amount, 'record_date': self.date}
        if jobwork_barcode_id and self.finishing_work_id.operation_id == config_record.full_finishing_id:
            vals.update({'workcenter_id': False, "remark": f'{self.remark}, {self.finishing_work_id.name} [Full Finishing Process]'})
        else:
            vals.update({'workcenter_id': wo.id, "remark": f"{self.remark},{self.finishing_work_id.name}"})
        if vals and amount > 0:
            self.env['inno.incentive.penalty'].create(vals)
