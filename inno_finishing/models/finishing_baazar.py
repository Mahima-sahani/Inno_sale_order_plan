from odoo import fields, models, _, api
from datetime import datetime
from odoo.exceptions import UserError, ValidationError, MissingError
import base64


class FinishingBaazar(models.Model):
    _name = "finishing.baazar"
    _description = 'Finishing Job Work'
    _rec_name = "reference"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    reference = fields.Char("Reference", default='/')
    finishing_work_id = fields.Many2one('finishing.work.order', string="Job Work No")
    subcontractor_id = fields.Many2one('res.partner', string='Subcontractor')
    date = fields.Date(string="Current Date", default=lambda *a: datetime.now())
    jobwork_received_ids = fields.One2many(comodel_name="jobwork.received", inverse_name="baazar_id")
    barcode_id = fields.Many2one(comodel_name='mrp.barcode')
    state = fields.Selection([('receiving', 'RECEIVING'), ('qc', 'Quality Check'), ('bill', 'Billing'),
                              ('done', 'DONE')], string='Status', default='draft')
    display_warning = fields.Boolean()
    is_bill = fields.Boolean()
    is_external = fields.Boolean(default=False)
    location_id = fields.Many2one(comodel_name='stock.location', string="Receive Location")
    bill_id = fields.Many2one(comodel_name='account.move', string="Invoice")
    rejected_qty = fields.Integer("Rejected", compute='_get_count')
    total_qty = fields.Integer("Received", compute='_get_count')
    verified_qty = fields.Integer("Verified", compute='_get_count')
    division_id = fields.Many2one(related='finishing_work_id.division_id')
    freight_amt = fields.Float(string="Amount", digits=(4, 2))
    is_binding = fields.Boolean(related='finishing_work_id.is_binding')
    is_choti = fields.Boolean(related='finishing_work_id.is_choti')
    operation_id = fields.Many2one(comodel_name='mrp.workcenter', related="finishing_work_id.operation_id",store=True)


    def _get_count(self):
        for rec in self:
            total_qty = len(self.jobwork_received_ids.ids)
            rejected = self.jobwork_received_ids.filtered(
                lambda wo: wo.state == 'reject')
            verified = self.jobwork_received_ids.filtered(
                lambda wo: wo.state == 'verified')
            self.rejected_qty = len(rejected)
            self.total_qty = total_qty
            self.verified_qty = len(verified)

    @api.onchange('barcode_id')
    def onchange_barcodes(self):
        is_barcoede_correct = self.check_barcode()
        if is_barcoede_correct:
            line = self.finishing_work_id.jobwork_barcode_lines.filtered(
                lambda pd: self.barcode_id.id in pd.barcode_id.ids).rate
            self.browse(self.id.origin).write({
                'jobwork_received_ids': [(0, 0, {'barcode_id': self.barcode_id.id, 'state': 'draft',
                                                 'baazar_id': self.id,
                                                 'rate_uom_id': line.rate_uom_id.name,
                                                 'rate': line.rate,
                                                 'finishing_work_id': self.finishing_work_id.id})]})
            self._cr.commit()
            self.display_warning = False
            self.barcode_id = False
        else:
            self.display_warning = True
            self.barcode_id = False

    def open_receiving_form(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _(f"{self.reference}"),
            'view_mode': 'form',
            'res_model': 'finishing.baazar',
            'res_id': self.id
        }

    def check_barcode(self):
        config_record = self.env['inno.config'].sudo().search([], limit=1)
        wo = self.barcode_id.current_process.filtered(
            lambda wo: self.finishing_work_id.sudo().operation_id.id in wo.workcenter_id.ids)
        is_correct = False
        full_finishing_bcodes = self.finishing_work_id.sudo().jobwork_barcode_lines.filtered(
            lambda line: self.barcode_id.id in
                         line.barcode_id.ids and
                         line.barcode_id.id not
                         in self.jobwork_received_ids.barcode_id.ids
                         and line.state in [
                             'draft',
                             'rejected'])
        if self.finishing_work_id.operation_id == config_record.full_finishing_id and self.barcode_id.full_finishing != False and full_finishing_bcodes:
            is_correct = True
        else:
            if wo and full_finishing_bcodes:
                is_correct = True
            else:
                is_correct = False
        return is_correct

    def open_vendor_bills(self):
        bills = self.env['account.move'].search([('finishing_bazaar_id', '=', self.id)])
        action = {
            'view_mode': 'form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
        }
        action.update({'view_type': 'form', 'res_id': bills[0].id})
        return action

    @api.model
    def default_get(self, fields_list):
        rec = super().default_get(fields_list)
        if rec.get('reference') == '/':
            rec.update({'reference': self.env['ir.sequence'].next_by_code('finishing_baazar_seq') or '/'})
        return rec

    def finish_bazaar(self):
        self.display_warning = False
        if not self.jobwork_received_ids:
            raise UserError(_("First you can scan the carpet barcode and then confirm it"))
        for rec in self.jobwork_received_ids:
            rec.state = 'received'
            rec.barcode_id.location_id = self.location_id.id
        self.state = 'qc'

    def reissue_rejected_barcodes(self):
        if self.jobwork_received_ids.filtered(lambda bl: bl.state == 'received'):
            raise UserError(_('QC is not finished for this Bazaar'))
        if self.jobwork_received_ids.filtered(lambda bl: bl.state == 'reject'):
            pdf = self.env.ref('inno_finishing.action_report_print_jobwork_reissue',
                               raise_if_not_found=False)._render_qweb_pdf('inno_finishing.'
                                                                          'action_report_print_jobwork_reissue',
                                                                          res_ids=self.id)[0]
            body = "Re-Issue Reports"
            self.message_past(pdf, body)
        self.state = 'bill'

    def receive_challan_records(self):
        pdf = self.env.ref('inno_finishing.action_report_print_receive_challan',
                           raise_if_not_found=False)._render_qweb_pdf('inno_finishing.'
                                                                      'action_report_print_receive_challan',
                                                                      res_ids=self.id)[0]
        body = "Challan Reports"
        self.message_past(pdf, body)

    def message_past(self, pdf, body):
        pdf = base64.b64encode(pdf).decode()
        attachment = self.env['ir.attachment'].sudo().create(
            {'name': f"{self.finishing_work_id.sudo().operation_id.name}{body}{self.reference}",
             'type': 'binary',
             'datas': pdf,
             'res_model': 'finishing.work.order',
             'res_id': self.id,
             })
        self.sudo().message_post(body=body, attachment_ids=[attachment.sudo().id])

    def generate_bill(self):
        # bill_id = self.env['account.move'].search([('finishing_bazaar_id','=', self.id)], limit=1)
        if not self.bill_id:
            check_verified = self.jobwork_received_ids.filtered(lambda rec: rec.state == 'verified')
            if check_verified:
                config_id = self.env['inno.config'].sudo().search([], limit=1)
                penalty_product = config_id.penalty_product_id
                incentive_product = config_id.incentive_product_id
                if not penalty_product or not incentive_product:
                    raise UserError("Please Ask your admin to configure Incentive and Penalty Products.")
                self.sudo().create_bill(penalty_product.id, incentive_product.id)
                self.return_finishing_status()
                self.button_done_bazaar()
            else:
                self.state = 'done'
        else:
            raise UserError("Baazar Bill has already been generated.")

    def button_done_bazaar(self):
        if self.bill_id:
            self.state = 'done'
            self.is_bill = True
            self.finishing_work_id.get_bills_count()
        jobwork_barcodes_lines = self.finishing_work_id.sudo().jobwork_barcode_lines.filtered(
            lambda rec: rec.state in ["draft", "rejected"])
        if not jobwork_barcodes_lines:
            self.finishing_work_id.sudo().write(
                {'status': 'done'})
        self.receive_challan_records()

    def create_bill(self, penalty_product, incentive_product):
        journal_id = self.env['inno.config'].sudo().search([], limit=1).finishing_journal_id
        tax_id = self.subcontractor_id.property_account_position_id.tax_ids.tax_dest_id
        if not journal_id:
            raise UserError(_("Please ask your admin to set weaving Journal"))
        invoice_lines = self.prepare_invoice_lines(penalty_product, incentive_product, journal_id, tax_id)
        bill_id = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.subcontractor_id.id,
            'date': fields.Datetime.now(),
            'invoice_date': fields.Datetime.now(),
            'finishing_work_id': self.finishing_work_id.id,
            'finishing_bazaar_id': self.id,
            'invoice_line_ids': invoice_lines,
            'journal_id': journal_id.id
        })
        tds_percent = 20 if not self.subcontractor_id.is_pan_aadhar_link or not self.subcontractor_id.pan_no else 1 if \
            self.subcontractor_id.pan_no[3] in ['p', 'P'] else 2
        tds_ammount = (bill_id.amount_untaxed / 100) * tds_percent
        bill_id.write({'invoice_line_ids': [
            (0, 0, {'display_type': 'line_section', 'name': 'TDS'}),
            (0, 0, {'quantity': 1, 'price_unit': -tds_ammount,
                    'account_id': self.env['account.account'].search(
                        [('name', '=', 'TDS Receivable')], limit=1).id,
                    'name': f"{tds_percent}% TDS Deduction"
                    })
        ]})
        self.bill_id = bill_id.id

    def prepare_invoice_lines(self, penalty_product, incentive_product, journal_id, tax_id):
        amalytic_plan = self.env['account.analytic.plan'].search([('name', '=', 'Finishing')], limit=1)
        if not amalytic_plan:
            raise UserError(_("Ask Your admin to set analytic plan"))
        analytic_account = self.env['account.analytic.account'].search([
            ('plan_id', '=', amalytic_plan.id), ('name', '=', self.finishing_work_id.operation_id.name)])
        if not analytic_account:
            analytic_account = self.env['account.analytic.account'].create(
                {'plan_id': amalytic_plan.id, 'name': self.finishing_work_id.operation_id.name})
        invoice_lines = [(0, 0, {'display_type': 'line_section', 'name': 'Products'})]
        received_data = {
            product: len(
                self.jobwork_received_ids.filtered(lambda bl: bl.product_id.id == product and bl.state == 'verified'))
            for product in self.jobwork_received_ids.filtered(lambda bl: bl.state == 'verified').
            product_id.ids}
        for rec in self.finishing_work_id.rate_incentive_ids:
            for product, qty in received_data.items():
                rc = self.jobwork_received_ids.filtered(
                    lambda rc: rc.work_order_line_id.rate_incentive_id.id in rec.ids and product in rc.product_id.ids)
                if not rec.rate and rc:
                    raise UserError(
                        _(f"{rec.product_tmpl_id.name} price list not defined for {self.finishing_work_id.operation_id.name} process"))
                if rc:
                    invoice_lines.extend([
                        (0, 0, {'product_id': product, 'quantity': qty,
                                'price_unit': float(rec.rate * rc.mapped('total_area')[0]),
                                'inno_area': f"{rc.mapped('total_area')[0] * qty} {rec.unit}",
                                'tax_ids': [(4, tax_id.id)] if tax_id else False, 'inno_price': rec.rate,
                                'account_id': journal_id.default_account_id.id, 'analytic_distribution': {analytic_account.id: 100}})])
        pen_vals = [{'product_id': penalty_product, 'quantity': 1, 'price_unit': -self.get_penalty(ptype),
                     'account_id': journal_id.default_account_id.id, 'analytic_distribution': {analytic_account.id: 100},
                     'name': ptype} for ptype in
                    ['time_penalty', 'bazaar_penalty', 'qa_penalty', 're_printing', 'cancel']]
        penalty_vals = [(0, 0, val) for val in pen_vals if val.get('price_unit') < 0]
        if penalty_vals:
            invoice_lines.append((0, 0, {'display_type': 'line_section', 'name': 'Penalties'}))
            invoice_lines.extend(penalty_vals)
        if self.finishing_work_id.freight_amt > 0 and not self.finishing_work_id.is_freight:
            invoice_lines.append((0, 0, {'display_type': 'line_section', 'name': 'Freight Issue'}))
            invoice_lines.append(
                (0, 0, {'name': f" Freight Issue Amount for {self.sudo().finishing_work_id.name}"f" [{self.reference}]",
                        'quantity': 1, 'price_unit': -self.finishing_work_id.freight_amt,
                        'account_id': journal_id.default_account_id.id}))
            self.finishing_work_id.write({'is_freight': True})
        if self.freight_amt > 0:
            invoice_lines.append((0, 0, {'display_type': 'line_section', 'name': 'Freight Receive'}))
            invoice_lines.append(
                (0, 0,
                 {'name': f" Freight Receive Amount for {self.sudo().finishing_work_id.name}"f" [{self.reference}]",
                  'quantity': 1, 'price_unit': -self.freight_amt,
                  'account_id': journal_id.default_account_id.id}))
        model_id = self.env.ref('inno_finishing.model_finishing_work_order').id
        incentive = sum(self.env['inno.incentive.penalty'].search(
            [('type', '=', 'finishing_incentive'), ('model_id', '=', model_id),
             ('rec_id', '=', self.finishing_work_id.id),
             ('barcode_id', 'in', self.jobwork_received_ids.filtered(lambda bl: bl.state == 'verified').barcode_id.ids),
             ('rec_id', '=', self.finishing_work_id.id)]).mapped(
            "amount"))
        if incentive:
            invoice_lines.append((0, 0, {'display_type': 'line_section', 'name': 'Incentive'}))
            invoice_lines.append((0, 0, {'product_id': incentive_product, 'quantity': 1, 'price_unit': incentive,
                                         'account_id': journal_id.default_account_id.id,
                                         'analytic_distribution': {analytic_account.id: 100}}))
        return invoice_lines

    def get_penalty(self, ptype):
        model_id = self.env.ref('inno_finishing.model_finishing_work_order').id
        return sum(self.env['inno.incentive.penalty'].
                   search([('type', '=', ptype), ('model_id', '=', model_id),
                           ('rec_id', '=', self.finishing_work_id.id)]).mapped('amount'))

    def update_bazaar_status(self):
        bazaars_to_update = self.search([('state', '=', 'receiving'), ('date', '<', fields.Datetime.today())])
        bazaars_to_update.write({'state', '=', 'qc'})

    def return_finishing_status(self):
        if self.env['stock.picking'].search_count([('finishing_work_id', '=', self.finishing_work_id.id),
                                                   ('origin', '=',
                                                    f"Cancel/Main Job Work: {self.finishing_work_id.name}")]):
            rec = self.env['stock.picking'].search([('finishing_work_id', '=', self.finishing_work_id.id),
                                                    ('origin', '=',
                                                     f"Cancel/Main Job Work: {self.finishing_work_id.name}"),
                                                    ('state', '!=', 'done')])
            if rec:
                raise UserError(_("Please Validate the Return Picking"))
