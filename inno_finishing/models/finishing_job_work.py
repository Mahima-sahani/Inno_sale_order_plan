from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, MissingError
import base64
from datetime import datetime, timedelta


class FinishingJobWork(models.Model):
    _name = 'finishing.work.order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "name"
    _description = 'Finishing Job Work'

    name = fields.Char(string='Reference')
    subcontractor_id = fields.Many2one(comodel_name='res.partner', tracking=True)
    status = fields.Selection([('draft', 'DRAFT'), ('barcode', 'BARCODE'), ('allotment', 'WAITING RELEASE'),
                               ('release', 'RELEASE'), ('bill_generated', 'BILLING'),
                               ('return_waiting', 'WAITING FOR MATERAIL RETURN'),
                               ('qa', 'PROCESS QC'), ('baazar', 'BAAZAR'), ('hishabh', 'HISHABH'),
                               ('done', 'JOB FINISHED'), ('cancel', 'CANCEL'), ('return', 'RETURNED'), ],
                              string='Status', default='draft', tracking=True)
    operation_id = fields.Many2one(comodel_name='mrp.workcenter')
    is_external = fields.Boolean(default=False, tracking=True)
    issue_date = fields.Date(default=fields.Datetime.now)
    expected_date = fields.Date()
    color = fields.Integer(compute='compute_kanban_color', default=2)
    material_transfer_id = fields.Many2one(comodel_name='stock.picking')
    material_lines = fields.One2many(comodel_name="finishing.materials", inverse_name="finishing_work_id",
                                     string="Materials")
    baazar_lines_ids = fields.One2many(comodel_name="finishing.baazar", inverse_name="finishing_work_id",
                                       string="Baazar")
    company_id = fields.Many2one(comodel_name='res.company')
    barcode_id = fields.Many2one(comodel_name='mrp.barcode')
    display_warning = fields.Boolean()
    total_qty = fields.Integer("Quantity", compute='_get_count')
    quality_inspector_id = fields.Many2one(comodel_name="res.partner", string="Quality Inspector")
    quality_control_ids = fields.One2many("mrp.quality.control", "finish_jobwork_id", string="Quality Control")
    jobwork_barcode_lines = fields.One2many(comodel_name="jobwork.barcode.line", inverse_name="finishing_work_id",
                                            string="Barcodes")
    return_barcode_lines = fields.Many2many(comodel_name="jobwork.barcode.line", string="Barcodes")
    full_finishing_id = fields.Many2one("mrp.workcenter")
    is_qa = fields.Boolean()
    is_report = fields.Boolean()
    rejected_qty = fields.Integer("Quantity", compute='_get_count')
    cancel_qty = fields.Integer("Cancel", compute='_get_count')
    full_cancellation_penalty = fields.Float()
    bill_count = fields.Integer(compute='get_bills_count')
    cancel_picking_count = fields.Integer(compute='compute_delivery_return')
    is_accepted = fields.Boolean()
    is_return = fields.Boolean()
    is_materials = fields.Boolean()
    start_wo = fields.Char()
    barcode_status = fields.Char()
    location_id = fields.Many2one(comodel_name='stock.location', string="Location")
    division_id = fields.Many2one(comodel_name="mrp.division", string="Division")
    pattern_details = fields.Html("Pattern")
    time_incentive = fields.Float("Time Incentive")
    rate_incentive_ids = fields.One2many("rate.and.incentive", "finishing_work_id", string="Rate & Incentive", )
    freight_amt = fields.Float(string="Amount", digits=(4, 2))
    alloted_days = fields.Integer()
    is_binding = fields.Boolean()
    is_choti = fields.Boolean()
    material_state = fields.Boolean()
    is_full_finishing = fields.Boolean()
    is_rate = fields.Boolean()
    pattimurai = fields.Char(compute="check_letexing_with_pattimurai", )
    is_freight = fields.Boolean("Fright")
    currency_id = fields.Many2one('res.currency', 'Currency', required=True,
                                  default=lambda self: self.env.company.currency_id.id)

    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position',
                                         domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    tax_totals = fields.Binary(compute='_compute_tax_totals', exportable=False)
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all')
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all',
                                     tracking=True)
    picking_count = fields.Integer(compute='compute_delivery')

    def generate_bill_using_cron_for_finishing(self):
        baazar = self.env['finishing.baazar'].search([('state', '=', 'bill'), ('bill_id', '=', False)])
        for rec in baazar.finishing_work_id:
            rec.with_context(with_rate=True, order=self).action_create_invoice()

    def compute_delivery(self):
        for rec in self:
            cancel = self.env['stock.picking'].search_count([('finishing_work_id', '=', self.id)])
            rec.picking_count = cancel or 0

    def button_action_for_material_record(self):
        return {
            'name': 'Materials Records',
            'view_mode': 'form',
            'res_model': 'finishing.bom.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': "{'process': 'material'}"
        }

    def action_done(self):
        material_lines = self.material_lines.filtered(lambda ml: not ml.closed)
        if material_lines:
            raise UserError("Firstly close the material hishabh")
        else:
            self.status = 'done'

    def action_create_for_material_hishabh(self):
        if self.material_lines:
            return {
                'name': 'Material Hishabh',
                'view_mode': 'form',
                'res_model': 'finishing.amendreturn.wiz',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'context': "{'process': 'hishabh'}"
            }

    def action_create_for_material_credit_note(self):
        material_lines = self.material_lines.filtered(lambda ml: ml.closed and not ml.added_in_bill)
        config_id = self.env['inno.config'].sudo().search([], limit=1)
        journal_id = config_id.finishing_journal_id
        invoice_lines = [(0, 0, {'display_type': 'line_section', 'name': 'Material Hishabh'})]
        bill = False
        if material_lines and self.is_external:
            for rec in material_lines:
                if rec.qty_amended - rec.qty_return - rec.qty_retained if rec.extra else rec.qty_released - rec.qty_return > 0.0:
                    invoice_lines.append(
                        (0, 0, {'name': f"Material Hishabh {self.sudo().name}", 'product_id': rec.product_id.id,
                                'quantity': rec.qty_amended - rec.qty_return - rec.qty_retained if rec.extra else rec.qty_released - rec.qty_return,
                                'price_unit': -rec.rate,
                                'account_id': journal_id.default_account_id.id}))
                    rec.write({'added_in_bill': True})
                    bill = True
            if bill:
                self.env['account.move'].create({
                    'move_type': 'in_refund',
                    'partner_id': self.subcontractor_id.id,
                    'date': fields.Datetime.now(),
                    'invoice_date': fields.Datetime.now(),
                    'finishing_work_id': self.id,
                    'invoice_line_ids': invoice_lines,
                    'journal_id': journal_id.id
                })

    def check_rate_of_orders(self, baazr):
        for rec in baazr.jobwork_received_ids:
            if rec.rate > 0.00:
                continue
            else:
                return False
        return True

    def action_create_invoice(self):
        if self._context.get('with_rate'):
            receive_lines = self.baazar_lines_ids.filtered(
                lambda bl: not bl.bill_id and bl.state == 'bill' and self.check_rate_of_orders(
                    bl)).jobwork_received_ids.filtered(
                lambda
                    jr: jr.state == 'verified' and jr.work_order_line_id.state == 'accepted' and jr.barcode_id.id in jr.work_order_line_id.barcode_id.ids)
        else:
            receive_lines = self.baazar_lines_ids.filtered(
                lambda bl: not bl.bill_id and bl.state == 'bill').jobwork_received_ids.filtered(
                lambda
                    jr: jr.state == 'verified' and jr.work_order_line_id.state == 'accepted' and jr.barcode_id.id in jr.work_order_line_id.barcode_id.ids)
        if receive_lines:
            config_id = self.env['inno.config'].sudo().search([], limit=1)
            penalty_product = config_id.penalty_product_id
            incentive_product = config_id.incentive_product_id
            if not penalty_product or not incentive_product:
                raise UserError("Please Ask your admin to configure Incentive and Penalty Products.")
            journal_id = config_id.finishing_journal_id
            tax_id = self.subcontractor_id.property_account_position_id.tax_ids.tax_dest_id
            if not journal_id:
                raise UserError(_("Please ask your admin to set finishing Journal"))
            amalytic_plan = self.env['account.analytic.plan'].search([('name', '=', 'Finishing')], limit=1)
            if not amalytic_plan:
                raise UserError(_("Ask Your admin to set analytic plan"))
            analytic_account = self.env['account.analytic.account'].search([
                ('plan_id', '=', amalytic_plan.id), ('name', '=', self.operation_id.name)])
            if not analytic_account:
                analytic_account = self.env['account.analytic.account'].create(
                    {'plan_id': amalytic_plan.id, 'name': self.operation_id.name})
            invoice_lines = self.prepare_invoice_lines(penalty_product.id, incentive_product.id, journal_id, tax_id,
                                                       receive_lines, analytic_account)
            bill_id = self.env['account.move'].create({
                'move_type': 'in_invoice',
                'partner_id': self.subcontractor_id.id,
                'date': fields.Datetime.now(),
                'invoice_date': fields.Datetime.now(),
                'finishing_work_id': self.id,
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
                        })]})
            receive_lines.baazar_id.write({'bill_id': bill_id.id, 'state': 'done'})
            job_lines = self.jobwork_barcode_lines.filtered(lambda jbl: jbl.state in ['draft', 'rejected', 'received'])
            ml_lines = self.material_lines.filtered(lambda ml: not ml.closed)
            if not job_lines and not self.material_lines:
                self.status = 'done'
            elif not job_lines and not ml_lines:
                self.status = 'done'
            elif not job_lines and ml_lines:
                self.status = 'hishabh'

    def prepare_invoice_lines(self, penalty_product, incentive_product, journal_id, tax_id, receive_lines,
                              analytic_account):
        invoice_lines = [(0, 0, {'display_type': 'line_section', 'name': 'Products'})]
        received_data = {
            product: len(
                receive_lines.filtered(lambda bl: bl.product_id.id == product and bl.state == 'verified'))
            for product in receive_lines.product_id.ids}
        unit = {'sq_yard': 'Sq. Yard',
                'feet': 'Feet',
                'sq_feet': 'Sq. Feet',
                'choti': 'Sq. Meter', }
        for product, qty in received_data.items():
            rate_lines = receive_lines.filtered(lambda bl: bl.product_id.id == product and bl.state == 'verified')
            if 0.0 == rate_lines[0].rate:
                for rec in rate_lines:
                    rec.work_order_line_id._compute_rate_finishing()
            if 0.0 < rate_lines[0].rate:
                invoice_lines.extend([
                    (0, 0, {'product_id': product, 'quantity': qty, 'analytic_distribution': {analytic_account.id: 100},
                            'price_unit': float(rate_lines[0].rate * rate_lines.mapped('total_area')[0]),
                            'inno_area': f"{rate_lines.mapped('total_area')[0] * qty} {unit.get(rate_lines[0].unit)}",
                            'tax_ids': [(4, tax_id.id)] if tax_id else False, 'inno_price': rate_lines[0].rate,
                            'account_id': journal_id.default_account_id.id})])
            else:
                raise UserError(
                    _(f"{rate_lines[0].product_id.product_tmpl_id.name} price list not defined for {self.operation_id.name} process and order no {self.name}"))
        receive_lines.work_order_line_id.write({'invoice_status': 'invoiced'})
        pen_vals = [
            {'product_id': penalty_product, 'quantity': 1, 'price_unit': -self.get_penalty(ptype, receive_lines),
             'account_id': journal_id.default_account_id.id, 'tax_ids': [(4, tax_id.id)] if tax_id else False,
             'analytic_distribution': {analytic_account.id: 100},
             'name': ptype} for ptype in
            ['time_penalty', 'bazaar_penalty', 'qa_penalty', 're_printing', 'cancel']]
        penalty_vals = [(0, 0, val) for val in pen_vals if val.get('price_unit') < 0]
        if penalty_vals:
            invoice_lines.append((0, 0, {'display_type': 'line_section', 'name': 'Penalties'}))
            invoice_lines.extend(penalty_vals)
        if self.freight_amt > 0 and not self.is_freight:
            invoice_lines.append((0, 0, {'display_type': 'line_section', 'name': 'Freight Issue'}))
            invoice_lines.append(
                (0, 0, {'name': f" Freight Issue Amount for {self.sudo().name}",
                        'analytic_distribution': {analytic_account.id: 100},
                        'quantity': 1, 'price_unit': -self.freight_amt,
                        'tax_ids': [(4, tax_id.id)] if tax_id else False,
                        'account_id': journal_id.default_account_id.id}))
            self.write({'is_freight': True})
        material_lines = self.material_lines.filtered(lambda ml: ml.closed and not ml.added_in_bill)
        if material_lines and self.is_external:
            invoice_lines.append((0, 0, {'display_type': 'line_section', 'name': 'Material Hishabh'}))
            for rec in material_lines:
                invoice_lines.append(
                    (0, 0, {'name': f" Material Hishabh {self.sudo().name}", 'product_id': rec.product_id.id,
                            'tax_ids': [(4, tax_id.id)] if tax_id else False,
                            'quantity': rec.qty_amended - rec.qty_return - rec.qty_retained if rec.extra else rec.qty_released - rec.qty_return,
                            'price_unit': -rec.rate, 'analytic_distribution': {analytic_account.id: 100},
                            'account_id': journal_id.default_account_id.id}))
                rec.write({'added_in_bill': True})
        receive_amt = round(sum([rec.freight_amt for rec in receive_lines.baazar_id]), 2)
        if receive_amt > 0:
            invoice_lines.append((0, 0, {'display_type': 'line_section', 'name': 'Freight Receive'}))
            invoice_lines.append(
                (0, 0,
                 {'name': f" Freight Receive Amount for {self.sudo().name}",
                  'tax_ids': [(4, tax_id.id)] if tax_id else False,
                  'quantity': 1, 'price_unit': -receive_amt, 'analytic_distribution': {analytic_account.id: 100},
                  'account_id': journal_id.default_account_id.id}))
        model_id = self.env.ref('inno_finishing.model_finishing_work_order').id
        incentive = sum(self.env['inno.incentive.penalty'].search(
            [('type', '=', 'finishing_incentive'), ('model_id', '=', model_id),
             ('rec_id', '=', self.id),
             ('barcode_id', 'in', receive_lines.barcode_id.ids)]).mapped(
            "amount"))
        if incentive:
            invoice_lines.append((0, 0, {'display_type': 'line_section', 'name': 'Incentive'}))
            invoice_lines.append((0, 0, {'product_id': incentive_product, 'quantity': 1, 'price_unit': incentive,
                                         'analytic_distribution': {analytic_account.id: 100},
                                         'tax_ids': [(4, tax_id.id)] if tax_id else False,
                                         'account_id': journal_id.default_account_id.id}))
        return invoice_lines

    def get_penalty(self, ptype, receive_lines):
        model_id = self.env.ref('inno_finishing.model_finishing_work_order').id
        if ptype == 'cancel':
            line = self.jobwork_barcode_lines.filtered(lambda jb: not jb.cancel_penality and jb.state == 'cancel')
            cancel_penality = sum(self.env['inno.incentive.penalty'].
                                  search(
                [('type', '=', ptype), ('model_id', '=', model_id), ('barcode_id', 'in', line.barcode_id.ids),
                 ('rec_id', '=', self.id)]).mapped('amount'))
            line.write({'cancel_penality': True})
            return cancel_penality
        else:
            return sum(self.env['inno.incentive.penalty'].
                       search(
                [('type', '=', ptype), ('model_id', '=', model_id), ('barcode_id', 'in', receive_lines.barcode_id.ids),
                 ('rec_id', '=', self.id)]).mapped('amount'))

    def action_for_material_amended(self):
        pickings = self.env['stock.picking'].search([('finishing_work_id', '=', self.id),
                                                     ('origin', '=', f"Main Job Work: {self.name}")])
        if pickings.filtered(lambda pick: pick.state == 'draft'):
            raise UserError(_("All Initial stock should be released first before Amending Quanity\n"
                              "Please ask inventory manager to validate the delivery order(s)."))
        return {
            'name': 'Need more Quantity',
            'view_mode': 'form',
            'res_model': 'finishing.amendreturn.wiz',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': "{'process': 'amend'}"
        }

    def action_for_material_return(self):
        return {
            'name': 'Return Consumables',
            'view_mode': 'form',
            'res_model': 'finishing.amendreturn.wiz',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': "{'process': 'return'}"
        }

    @api.depends('jobwork_barcode_lines.price_total')
    def _amount_all(self):
        for order in self:
            order_lines = order.jobwork_barcode_lines

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

    @api.depends('jobwork_barcode_lines.price_subtotal', 'amount_total', 'amount_untaxed')
    def _compute_tax_totals(self):
        for order in self:
            order_lines = order.jobwork_barcode_lines
            order.tax_totals = self.env['account.tax']._prepare_tax_totals(
                [x._convert_to_tax_base_line_dict() for x in order_lines],
                order.currency_id or order.company_id.currency_id,
            )

    def check_letexing_with_pattimurai(self):
        config_id = self.env["inno.config"].sudo().search([], limit=1)
        if config_id.letexing_id == self.operation_id and self.is_external:
            self.pattimurai = f'{self.operation_id.name} + Pattimurai'
        else:
            self.pattimurai = f'{self.operation_id.name}'

    def check_rate(self):
        if self.status in ['release', 'baazar']:
            rate = False
            for rec in self.rate_incentive_ids:
                if rec.rate == 0:
                    rate = True
            self.is_rate = rate

    def button_confirm(self):
        """
        Confirm the finishing job order and created the record of material issue and carpet transfer.
        """
        for rec in self:
            config_id = self.env["inno.config"].sudo().search([], limit=1)
            if not rec.jobwork_barcode_lines:
                raise UserError(_("First you can scan the carpet barcode and then confirm it"))
            if rec.operation_id == config_id.full_finishing_id:
                self.change_status_for_full_finishing_barcode()
                rec.status = 'allotment'
                # rec.is_materials = True
                self.is_report = True
                self.is_full_finishing = True
            elif (self.operation_id.id in config_id.without_materials_operation_ids.ids):
                self.change_status_of_barcode()
                self.button_action_for_reports()
                rec.status = 'release'
            else:
                self.change_status_of_barcode()
                # rec.is_materials = True
                rec.status = 'allotment'
                self.is_report = True
            # self.details_rate_incentive(rec)
            self.check_letexing_with_pattimurai()

    @api.onchange('alloted_days')
    def onchange_alloted_days(self):
        if self.alloted_days < 0:
            raise UserError(_("You can't enter negative value."))
        if not self.issue_date:
            self.issue_date = datetime.now()
        if self.alloted_days > 0:
            self.expected_date = datetime.strptime(str(self.issue_date), "%Y-%m-%d") + timedelta(
                days=self.alloted_days)
        else:
            self.expected_date = False

    @api.onchange('expected_date')
    def onchange_expected_date(self):
        if self.expected_date:
            if self.expected_date < self.issue_date:
                raise UserError(_("You Can't set older dates than issue date"))
            self.alloted_days = (self.expected_date - self.issue_date).days
            self.barcode_status = 'Sunday' if self.expected_date.weekday() == 6 else False
        else:
            self.barcode_status = False

    def create_rate_list_data(self):
        for rec in self.jobwork_barcode_lines.product_id:
            rate, fix_inc, exp_incentive = rec.sudo().calculate_product_rate(self.operation_id,
                                                                             self.subcontractor_id.is_far,
                                                                             self.is_external, True)
            line_rate = self.rate_incentive_ids.filtered(
                lambda pd: rec.product_tmpl_id.id in pd.product_tmpl_id.ids)
            area, unit = self.get_total_area_and_unit_of_product(rec)
            if not line_rate:
                self.write(
                    {'rate_incentive_ids': [
                        (0, 0, {"product_tmpl_id": rec.product_tmpl_id.id, 'fixed_incentive': fix_inc,
                                'expire_incentive': exp_incentive,
                                'is_sample': True if self.jobwork_barcode_lines.filtered(
                                    lambda
                                        pd: pd.barcode_id.mrp_id.is_sample and rec.product_tmpl_id.id in pd.product_id.product_tmpl_id.ids) else False,
                                'unit': unit,
                                'qty': self.jobwork_barcode_lines.filtered(lambda
                                                                               pd: rec.product_tmpl_id.id in pd.product_id.product_tmpl_id.ids).__len__()})]})
            else:
                line_rate.write({'fixed_incentive': fix_inc, 'expire_incentive': exp_incentive, })
            lines = self.jobwork_barcode_lines.filtered(lambda bl: bl.product_id.id in rec.ids)
            if lines:
                lines.write({'total_area': area, 'unit': unit, 'rate': rate})
            self._cr.commit()

    def update_rate_and_area_with_master(self):
        self.create_rate_list_data()
        return {
            'name': "Update Area and Rate",
            'view_mode': 'form',
            'res_model': 'inno.sample.rate.update',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'from_finishing': True}
        }

    def update_rate_and_area(self):
        return {
            'name': "Update Area and Rate",
            'view_mode': 'form',
            'res_model': 'inno.sample.rate.update',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'from_finishing': True}
        }

    def update_bill(self):
        bills = self.baazar_lines_ids.bill_id
        unit = {'sq_yard': 'Sq. Yard',
                'feet': 'Feet',
                'sq_feet': 'Sq. Feet',
                'choti': 'Sq. Meter', }
        for bill in bills:
            baazar = self.baazar_lines_ids.filtered(lambda bl: bl.bill_id.id in bill.ids)
            lines = baazar.jobwork_received_ids.filtered(lambda st: st.state == 'verified')
            products = lines.product_id
            if bill.state == 'posted':
                bill.button_draft()
            for prd in products:
                verified_lines = lines.filtered(lambda li: li.product_id.id in prd.ids)
                invoice_line = bill.invoice_line_ids.filtered(
                    lambda ivl: ivl.product_id.id in prd.ids)
                if invoice_line:
                    invoice_line.write({
                        'inno_area': f"{verified_lines.mapped('total_area')[0] * verified_lines.__len__()} {unit.get(verified_lines[0].unit)}",
                        'inno_price': verified_lines[0].rate, 'quantity': verified_lines.__len__(),
                        'price_unit': float(verified_lines[0].rate * verified_lines.mapped('total_area')[0])})
                    self.message_post(
                        body=f"<b>Updated Bill :</b><br/> <b>{bill.name}  {prd.default_code} New rate {round(float(verified_lines[0].rate * verified_lines.mapped('total_area')[0]), 3)}</b> ")
            if bill.state == 'draft':
                bill.invoice_line_ids.filtered(lambda ivl: 'TDS Deduction' in ivl.name).unlink()
                tds_percent = 20 if not self.subcontractor_id.is_pan_aadhar_link or not self.subcontractor_id.pan_no else 1 if \
                    self.subcontractor_id.pan_no[3] in ['p', 'P'] else 2
                tds_ammount = (bill.amount_untaxed / 100) * tds_percent
                bill.write({'invoice_line_ids': [
                    (0, 0, {'quantity': 1, 'price_unit': -tds_ammount,
                            'account_id': self.env['account.account'].search(
                                [('name', '=', 'TDS Receivable')], limit=1).id,
                            'name': f"{tds_percent}% TDS Deduction"
                            })]})
                bill.action_post()

    def get_total_area_and_unit_of_product(self, product):
        if product and self.operation_id:
            config_id = self.env["inno.config"].sudo().search([], limit=1)
            rate = product.product_tmpl_id.rate_list_id.filtered(
                lambda ln: self.operation_id.id in ln.work_center_id.ids and ln.uom_id)
            if self.operation_id.id in [config_id.binding_id.id, config_id.gachhai_id.id]:
                if self.operation_id.id == config_id.binding_id.id:
                    if product.product_tmpl_id.binding_prm == 'width':
                        return product.inno_finishing_size_id.len_parm, 'feet'
                    elif product.product_tmpl_id.binding_prm == 'length':
                        return product.inno_finishing_size_id.width_parm, 'feet'
                    elif product.product_tmpl_id.binding_prm == 'both':
                        return product.inno_finishing_size_id.perimeter, 'feet'
                if self.operation_id.id == config_id.gachhai_id.id:
                    if product.choti > 0:
                        return product.choti, 'choti'
                    else:
                        if product.product_tmpl_id.gachhai_prm == 'width':
                            return product.inno_finishing_size_id.len_parm, 'feet'
                        elif product.product_tmpl_id.gachhai_prm == 'length':
                            return product.inno_finishing_size_id.width_parm, 'feet'
                        elif product.product_tmpl_id.gachhai_prm == 'both':
                            return product.inno_finishing_size_id.perimeter, 'feet'
            else:
                if rate:
                    if rate[0].uom_id.name == 'Sq. Yard':
                        return product.finishing_area, 'sq_yard'
                    elif rate.uom_id.name == 'ft²':
                        return product.sq_feet_area, 'sq_feet'
                    elif rate.uom_id.name == 'm²':
                        return product.area_sq_mt, 'm²'
                else:
                    return product.finishing_area, 'sq_yard'

    def _compute_accepted(self):
        if self.status != "draft":
            accepted = self.jobwork_barcode_lines.filtered(
                lambda wo: wo.state == 'accepted')
            if len(accepted) == len(self.jobwork_barcode_lines):
                self.status = 'done'
                self.is_accepted = True
        else:
            self.is_accepted = False

    def compute_delivery_return(self):
        for rec in self:
            cancel = self.env['stock.picking'].search_count([('finishing_work_id', '=', self.id),
                                                             (
                                                                 'origin', '=', f"Cancel/Main Job Work: {self.name}")])
            rec.cancel_picking_count = cancel or 0

    def get_bills_count(self):
        for rec in self:
            rec.sudo().write(
                {'bill_count': self.env['account.move'].search_count([('finishing_work_id', '=', self.id)])})

    def open_vendor_bills(self):
        bills = self.env['account.move'].search([('finishing_work_id', '=', self.id)])
        action = {
            'name': _(f"Bill(s) for {self.name}"),
            'view_mode': 'form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
        }
        if len(bills) > 1:
            action.update({'view_mode': 'tree,form', 'domain': [('id', 'in', bills.ids)]})
        else:
            action.update({'view_type': 'form', 'res_id': bills[0].id})
        return action

    def _get_count(self):
        for rec in self:
            total_qty = len(self.jobwork_barcode_lines.ids)
            rec.total_qty = total_qty
            rejected = self.jobwork_barcode_lines.filtered(
                lambda wo: wo.state == 'rejected')
            cancel = self.jobwork_barcode_lines.filtered(
                lambda wo: wo.state == 'cancel')
            self.rejected_qty = len(rejected)
            self.cancel_qty = len(cancel)

    def open_cancel_return(self):
        picking_ids = self.env['stock.picking'].search([('finishing_work_id', '=', self.id),
                                                        ('origin', '=', f"Cancel/Main Job Work: {self.name}")])
        return {'name': "Job Work Cancellation", 'view_mode': 'tree,form', 'res_model': 'stock.picking',
                'type': 'ir.actions.act_window', 'domain': [('id', 'in', picking_ids.ids)]}

    def action_cancel(self):
        if self.status == 'draft':
            for rec in self.jobwork_barcode_lines:
                rec.barcode_id.write(
                    {'location_id': self.location_id.id, 'full_finishing': False, 'current_process': False,
                     'finishing_jobwork_id': False})
                rec.unlink()
        else:
            if self.env['stock.picking'].search_count([('finishing_work_id', '=', self.id),
                                                       ('origin', '=', f"Cancel/Main Job Work: {self.name}")]):
                rec = self.env['stock.picking'].search([('finishing_work_id', '=', self.id),
                                                        ('origin', '=',
                                                         f"Cancel/Main Job Work: {self.name}"),
                                                        ('state', '!=', 'done')])
                if rec:
                    raise UserError(_("Please Validate the Return Picking"))
                self.cancelation_process()

    def cancelation_process(self):
        self.status = 'return'

    def action_return(self):
        return {
            'name': _(f"Cancel Job Work {self.name}"),
            'view_mode': 'form',
            'res_model': 'inno.return.job.work',
            'context': {'default_job_work_id': self.id},
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def button_action_for_reports(self):
        """
        Generate a job work sheet and attached it to chatter.
        """
        pdf = self.env.ref('inno_finishing.action_report_print_material_allocation',
                           ).sudo()._render_qweb_pdf('inno_finishing.action_report_print_material_allocation',
                                                     res_ids=self.id)[0]
        body = "Finishing Job Work Generated"
        self.message_past(pdf, body)
        if not self.material_lines:
            pdf = self.env.ref('inno_finishing.action_report_operation_gate_pass',
                               ).sudo()._render_qweb_pdf('inno_finishing.action_report_operation_gate_pass',
                                                         res_ids=self.id)[0]
            body = "Gate Pass Generated"
            self.message_past(pdf, body)
        self.is_report = False
        self.status = 'release'
        self.check_rate()

    def return_reports_job_works(self):
        if not self.company_id:
            self.company_id = False
        pdf = self.env.ref('inno_finishing.action_report_print_return',
                           ).sudo()._render_qweb_pdf('inno_finishing.action_report_print_return',
                                                     res_ids=self.id)[0]
        body = "Finishing Return Reports"
        self.message_past(pdf, body)

    def message_past(self, pdf, body):
        pdf = base64.b64encode(pdf).decode()
        attachment = self.env['ir.attachment'].create({'name': f"{body}{self.name}",
                                                       'type': 'binary',
                                                       'datas': pdf,
                                                       'res_model': 'finishing.work.order',
                                                       'res_id': self.id,
                                                       })
        self.message_post(body=body, attachment_ids=[attachment.id])

    def button_for_quality_inspector(self):
        """
        Will verify the stock pickings and quality manager assigned to job work.
        """
        # self.validate_pickings()
        if not self.quality_inspector_id:
            raise UserError(_("Please Assign a Quality Manager First!"))
        self.assign_qa_job()
        self.status = 'qa'

    def assign_qa_job(self):
        """
        Generate a QC record for qc manager.
        """
        self.env['mrp.quality.control'].sudo().create({'name': f'QC for {self.name}', 'finish_jobwork_id': self.id,
                                                       'subcontractor_id': self.subcontractor_id.id,
                                                       'qc_manager_id': self.quality_inspector_id.id,
                                                       'quality_state': 'draft'})

    def create_picking(self, move, type, source, destination):
        pick_id = self.env['stock.picking'].sudo().create({
            'name': type.sequence_id.next_by_id(),
            'partner_id': self.subcontractor_id.id,
            'picking_type_id': type.id,
            'location_id': source,
            'location_dest_id': destination,
            'move_ids': move,
            'state': 'draft',
            'origin': f"Finishing Job Work: {self.name}",
            'finishing_work_id': self.id
        })
        self.material_transfer_id = pick_id.id
        return pick_id

    def prepare_job_stock_move(self, source, destination, lines):
        """
        Prepare the stock move line as per the component set in the selected operation
        """
        moves = []
        alloted_components = lines
        moves.extend([(0, 0, {'name': f"Test",
                              'product_id': component.product_id.id,
                              'product_uom_qty': component.product_qty - component.qty_previous,
                              'product_uom': component.uom_id.id,
                              'location_id': source,
                              'location_dest_id': destination
                              }) for component in alloted_components])
        return moves

    def open_material_transfer(self):
        """
        Opens the material issue record.
        """
        record = self.env['stock.picking'].search([('finishing_work_id', '=', self.id), ])
        return self.open_pickings(record, 'Delivery')

    def open_pickings(self, record, type):
        action = {
            'name': _(type),
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
        }
        if len(record) > 1:
            action.update({'view_mode': 'tree,form', 'domain': [('id', 'in', record.ids)]})
        else:
            action.update({'view_type': 'form', 'res_id': record[0].id})
        return action

    def compute_kanban_color(self):
        for rec in self:
            rec.color = 2 if rec.status == 'draft' else 4 if rec.status == 'issue' else 10

    @api.onchange('operation_id')
    def onchange_operation_id(self):
        """
        Add domain to the location id field based on operation
        """
        if self.operation_id:
            return {'domain': {
                'location_id': [('id', 'in', self.operation_id.location_id.ids)]
            }}
        else:
            return {'domain': {
                'location_id': [('id', 'in', [])]
            }}

    def change_status_for_full_finishing_barcode(self):
        for bcode in self.jobwork_barcode_lines.barcode_id:
            bcode.state = '7_finishing'

    def change_status_of_barcode(self):
        for bcode in self.jobwork_barcode_lines.barcode_id:
            for rec in bcode.sudo().mrp_id:
                wo = rec.workorder_ids.filtered(lambda wo: self.operation_id.id in wo.workcenter_id.ids)
                if wo and not bcode.full_finishing:
                    bcode.sudo().write({'state': '7_finishing', 'current_process': wo.id,
                                        'next_process': self.env['mrp.workorder'].search(
                                            [('parent_id', '=', wo.id)]).id})
                else:
                    if bcode.full_finishing == True:
                        bcode.write({'state': '7_finishing', 'current_process': wo.id})

    def button_ready_bazaar(self):
        if self.baazar_lines_ids.filtered(lambda baz: baz.date == fields.Datetime.today().date()):
            raise UserError(_("There is already a receiving created for today."))
        self.env['finishing.baazar'].create({'finishing_work_id': self.id, 'subcontractor_id': self.subcontractor_id.id,
                                             'is_external': self.is_external,
                                             'state': 'receiving'})
        self.status = 'baazar'

    def generate_gate_pass(self):
        pass
