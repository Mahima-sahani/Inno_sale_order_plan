from odoo import fields, models, _, api
from datetime import datetime
from dateutil import relativedelta
from odoo.exceptions import UserError


class BaazaProductLines(models.Model):
    _name = "mrp.baazar.product.lines"
    _description = 'Baazar Product Lines'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = 'barcode'

    main_jobwork_id = fields.Many2one(comodel_name='main.jobwork')
    job_work_id = fields.Many2one(comodel_name='mrp.job.work')
    product_id = fields.Many2one(related="barcode.product_id", string="Product")
    state = fields.Selection([('received', 'RECEIVED'), ('verified', 'VERIFIED'), ('reject', 'Rejected')],
                             string='Status')
    date = fields.Date(string="Current Date", default=lambda *a: datetime.now())
    expected_weight = fields.Float("Standard Weight", compute='_compute_expected_weight', store=True)
    actual_weight = fields.Float("Actual Weight")
    bazaar_id = fields.Many2one("main.baazar", string="Main Bazaar")
    barcode = fields.Many2one(comodel_name='mrp.barcode')
    uom_id = fields.Many2one(related='job_work_id.uom_id', string='UOM')
    penalty = fields.Float()
    remark = fields.Char()
    division_id = fields.Many2one(related='bazaar_id.division_id')
    is_full_penalty = fields.Boolean(string='Is Full Penalty?')
    space = fields.Char('    ', readonly=True)

    @api.depends('product_id')
    def _compute_expected_weight(self):
        for rec in self:
            rec.expected_weight = sum(rec.product_id.bom_ids.filtered(
                lambda bom: bom.product_id.id == rec.product_id.id).bom_line_ids.mapped('product_qty')) or 0.0

    def do_pass_or_reject(self):
        self.state = self._context.get('status')
        if self._context.get('status') == 'verified':
            if self.actual_weight < 0.1:
                raise UserError(_("You Can't Validate Barcode Without adding the Actual Weight."))
            if self.penalty and not self.remark:
                raise UserError(_("Please Add remark for the penalty you have added to this barcode."))
            self.sudo().update_finished_qty()
            vals = {'process_finished': [(4, self.barcode.current_process.id)], 'current_process': False,
                    'state': '5_verified', 'location_id': self.bazaar_id.location_id.id}
            penalties = []
            if self.penalty:
                penalties.append((0, 0, {'type': 'qa_penalty', 'record_date': fields.Datetime.now(),
                                         'amount': self.penalty if self.is_full_penalty else self.penalty * self.job_work_id.area,
                                         'remark': self.remark, 'rec_id': self.main_jobwork_id.id,
                                         'workcenter_id': self.barcode.current_process.id,
                                         'model_id': self.env.ref('innorug_manufacture.model_main_jobwork').id}))
            config_record = self.env['inno.config'].sudo().search([], limit=1)
            fragment_penalty = config_record.fragment_penalty
            allowed_fragments = self.sudo().main_jobwork_id.total_chunks
            if allowed_fragments < 1 or fragment_penalty < 0.1:
                raise UserError(_("Please ask your admin to configure bazaar Fragments and Penalties"))
            penalty_amount = self.barcode.sudo().product_id.mrp_area * fragment_penalty
            if self.sudo().main_jobwork_id.baazar_lines_ids.__len__() > allowed_fragments:
                penalties.append((0, 0, {'type': 'bazaar_penalty', 'record_date': fields.Datetime.now(),
                                         'amount': penalty_amount, 'remark': f" Product Received in more "
                                                                             f"than {allowed_fragments} bazaars",
                                         'workcenter_id': self.barcode.current_process.id,
                                         'rec_id': self.main_jobwork_id.id,
                                         'model_id': self.env.ref('innorug_manufacture.model_main_jobwork').id}))
            main_job_work = self.sudo().main_jobwork_id
            penalty_amount = self.barcode.product_id.mrp_area * main_job_work.time_penalty
            if penalty_amount > 0.0 and (self.sudo().bazaar_id.date.date() > main_job_work.expected_received_date +
                                         relativedelta.relativedelta(days=main_job_work.extra_time)):
                penalties.append((0, 0, {'type': 'time_penalty', 'record_date': fields.Datetime.now(),
                                         'amount': penalty_amount, 'remark': f"Product Received After "
                                                                             f"The Total allwed Days",
                                         'workcenter_id': self.barcode.current_process.id,
                                         'rec_id': self.sudo().main_jobwork_id.id,
                                         'model_id': self.env.ref('innorug_manufacture.model_main_jobwork').id}))
            if penalties:
                vals.update({'pen_inc_ids': penalties})
            self.barcode.write(vals)
            if self.sudo().main_jobwork_id.is_full_finish:
                self.barcode.move_barcode_inventory()
        self.sudo().check_and_verify_bazaar()

    def check_and_verify_bazaar(self):
        bz_lines = self.bazaar_id.baazar_lines_ids
        if bz_lines.filtered(lambda bl: bl.state == 'received'):
            return
        elif bz_lines.filtered(lambda bl: bl.state == 'reject'):
            return
        else:
            self.bazaar_id.state = 'incentive'

    def update_finished_qty(self):
        self.job_work_id.received_qty += 1
        self.job_work_id.mrp_work_order_id.finished_qty += 1
