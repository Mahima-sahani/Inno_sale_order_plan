import base64
from odoo import fields, models, _, api
from datetime import datetime
from odoo.exceptions import UserError, ValidationError, MissingError


class MainBaazar(models.Model):
    _name = "main.baazar"
    _description = 'Main Job Work'
    _rec_name = "reference"
    _inherit = ['mail.thread', 'mail.activity.mixin']

    reference = fields.Char("Reference", default='/')
    main_jobwork_id = fields.Many2one('main.jobwork', string="Job Work No")
    subcontractor_id = fields.Many2one('res.partner', string='Subcontractor')
    date = fields.Datetime(string="Bazaar Date", default=lambda *a: datetime.now(), readonly="1")
    baazar_lines_ids = fields.One2many(comodel_name="mrp.baazar.product.lines", inverse_name="bazaar_id")
    state = fields.Selection([('receiving', 'RECEIVING'), ('qc', 'Quality Check'), ('incentive', 'Incentive'),
                              ('bill', 'Billing'), ('done', 'Bill Generated'), ('returned', 'All Barcode Returned')],
                             string='Status', default='draft')
    scanned_barcode_id = fields.Many2one(comodel_name='mrp.barcode', string='Scan Barcodes')
    display_scan_warning = fields.Char(store=False)
    division_id = fields.Many2one(related='main_jobwork_id.division_id')
    location_id = fields.Many2one(comodel_name='stock.location', string="Bazaar Location")
    bill_count = fields.Integer(compute='_compute_bills')

    def update_barcode_location(self):
        for rec in self:
            rec.baazar_lines_ids.barcode.write({'location_id': rec.location_id.id})

    def button_incentive(self):
        self.state = 'bill'
        self.env['inno.incentive'].create([{
            'barcode_id': val.barcode.id, 'product_id': val.product_id.id, 'bazaar_id': self.id,
            'uom_id': val.uom_id.id, 'incentive_added': False, 'bazaar_line_id': val.id
        } for val in self.baazar_lines_ids.filtered(lambda bl: bl.state == 'verified')])
        if self._context.get('incentive'):
            return {
                'name': _(f"Incentive for {self.reference}"),
                'view_mode': 'tree',
                'res_model': 'inno.incentive',
                'type': 'ir.actions.act_window',
                'target': 'new',
                'domain': [('incentive_added', '=', False), ('bazaar_id', '=', self.id)]
            }

    def _compute_bills(self):
        for rec in self:
            rec.bill_count = self.env['account.move'].sudo().search_count([('bazaar_id', '=', rec.id)])

    @api.model
    def default_get(self, fields_list):
        rec = super().default_get(fields_list)
        if rec.get('reference') == '/':
            rec.update({'reference': self.env['ir.sequence'].next_by_code('main_bazaar_seq') or '/'})
        return rec

    @api.onchange('scanned_barcode_id')
    def onchange_barcodes(self):
        message = self.check_barcode()
        if not message:
            self.browse(self.id.origin).write({
                'baazar_lines_ids': [(0, 0, {'main_jobwork_id': self.sudo().main_jobwork_id.id, 'state': 'received',
                                             'barcode': self.scanned_barcode_id.id,
                                             'job_work_id': self.sudo().main_jobwork_id.jobwork_line_ids.filtered(
                                                 lambda jw: self.scanned_barcode_id.id in jw.barcodes.ids).id})]})
            self._cr.commit()
            self.display_scan_warning = False
            self.scanned_barcode_id = False
        else:
            self.display_scan_warning = message
            self.scanned_barcode_id = False

    def check_barcode(self):
        message = False
        if self.scanned_barcode_id.state != '3_allocated':
            message = 'Barcode you have scanned is not attached to this job.'
        elif self.scanned_barcode_id.id not in self.main_jobwork_id.jobwork_line_ids.barcodes.ids:
            message = 'Barcode You have scanned is not allocated to this Job Work.'
        elif (self.scanned_barcode_id.id in self.main_jobwork_id.baazar_lines_ids.baazar_lines_ids.
                filtered(lambda bl: bl.state in ['verified', 'received']).barcode.ids):
            message = 'Barcode You have scanned is either accepted or waiting for QC in another Bazaar.'
        return message

    def finish_bazaar(self):
        if self.baazar_lines_ids.filtered(lambda bl: bl.state in ['received', 'reject']):
            self.state = 'qc'
        else:
            self.state = 'incentive'

    def reissue_rejected_barcodes(self):
        if self.baazar_lines_ids.filtered(lambda bl: bl.state == 'received'):
            raise UserError(_('QC is not finished for this Bazaar'))
        pdf = self.env.ref('innorug_manufacture.action_report_print_jobwork_reissue',
                           raise_if_not_found=False).sudo()._render_qweb_pdf('innorug_manufacture.'
                                                                             'action_report_print_jobwork_reissue',
                                                                             res_ids=self.id)[0]
        pdf = base64.b64encode(pdf).decode()
        attachment = self.env['ir.attachment'].create({'name': f"Weaving Job Work {self.reference}",
                                                       'type': 'binary',
                                                       'datas': pdf,
                                                       'res_model': 'main.baazar',
                                                       'res_id': self.id,
                                                       })
        self.state = 'incentive' if any(self.baazar_lines_ids.filtered(lambda bl: bl.state == 'verified')) \
            else 'returned'

    def generate_bill(self):
        if self.bill_count:
            return
        if not self.baazar_lines_ids.filtered(lambda bl: bl.state == 'verified'):
            self.state = 'done'
            return
        config_id = self.env['inno.config'].sudo().search([], limit=1)
        penalty_product = config_id.penalty_product_id
        incentive_product = config_id.incentive_product_id
        if not penalty_product or not incentive_product:
            raise UserError("Please Ask your admin to configure Weaving Incentive and Penalty Products.")
        self.sudo().create_bill(penalty_product.id, incentive_product.id)
        self._compute_bills()
        self.state = 'done'

    def open_vendor_bills(self):
        bills = self.env['account.move'].search([('bazaar_id', '=', self.id)])
        action = {
            'name': _(f"Bill(s) for {self.reference}"),
            'view_mode': 'form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
        }
        if len(bills) > 1:
            action.update({'view_mode': 'tree,form', 'domain': [('id', 'in', bills.ids)]})
        else:
            action.update({'view_type': 'form', 'res_id': bills[0].id})
        return action

    def create_bill(self, penalty_product, incentive_product):
        journal_id = self.env['inno.config'].sudo().search([], limit=1).weaving_journal_id
        if not journal_id:
            raise UserError(_("Please ask your admin to set weaving Journal"))
        invoice_lines = self.prepare_invoice_lines(penalty_product, incentive_product, journal_id)
        bill = self.env['account.move'].create({
            'move_type': 'in_invoice',
            'partner_id': self.subcontractor_id.id,
            'date': fields.Datetime.now(),
            'invoice_date': fields.Datetime.now(),
            'job_work_id': self.main_jobwork_id.id,
            'bazaar_id': self.id,
            'invoice_line_ids': invoice_lines,
            'journal_id': journal_id.id
        })
        try:
            tds_percent = 20 if not self.subcontractor_id.is_pan_aadhar_link or not self.subcontractor_id.pan_no else 1 if \
                self.subcontractor_id.pan_no[3] in ['p', 'P'] else 2
        except Exception as ex:
            raise UserError(_("Please check Pan Number, Wrong PAN found."))
        tds_ammount = (bill.amount_untaxed / 100) * tds_percent
        retention_amount = (bill.amount_untaxed / 100) * 5 if self.division_id.name == 'KNOTTED' else (
                                                                                                              bill.amount_untaxed / 100) * 10
        bill.write({'invoice_line_ids': [(0, 0, {'display_type': 'line_section', 'name': 'Retention'}),
                                         (0, 0, {'quantity': 1, 'price_unit': -retention_amount,
                                                 'account_id': journal_id.default_account_id.id,
                                                 'name': f"Retention Amount for {self.sudo().main_jobwork_id.reference}"
                                                         f" [{self.reference}]"}),
                                         (0, 0, {'display_type': 'line_section', 'name': 'TDS'}),
                                         (0, 0, {'quantity': 1, 'price_unit': -tds_ammount,
                                                 'account_id': self.env['account.account'].search(
                                                     [('name', '=', 'TDS Receivable')], limit=1).id,
                                                 'name': f"{tds_percent}% TDS Deduction"
                                                 })
                                         ]})
        self.env['inno.incentive.penalty'].create({
            'partner_id': self.subcontractor_id.id,
            'remark': f"{self.sudo().main_jobwork_id.reference} [{self.reference}]",
            'record_date': fields.Datetime.now(),
            'amount': retention_amount,
            'type': 'retention'
        })
        amount = bill.tax_totals.get('amount_total')
        round_amount = amount % 1
        up_round_off = self.env['account.cash.rounding'].sudo().search([('name', '=', 'Round UP')])
        dowm_round_off = self.env['account.cash.rounding'].sudo().search([('name', '=', 'Round Down')])
        if round_amount > 0 and round_amount < 0.50:
            bill.write({'invoice_cash_rounding_id': dowm_round_off.id})
        elif round_amount > 0:
            bill.write({'invoice_cash_rounding_id': up_round_off.id})

    def prepare_invoice_lines(self, penalty_product, incentive_product, journal_id):
        tax_id = self.subcontractor_id.property_account_position_id.tax_ids.tax_dest_id
        invoice_lines = [(0, 0, {'display_type': 'line_section', 'name': 'Products'})]
        received_data = {product: len(
            self.baazar_lines_ids.filtered(lambda bl: bl.product_id.id == product and bl.state == 'verified'))
            for product in self.baazar_lines_ids.filtered(lambda bl: bl.state == 'verified').
            product_id.ids}
        fix_inc = 0
        for product, qty in received_data.items():
            jw_id = self.baazar_lines_ids.job_work_id.filtered(lambda jw: jw.product_id.id == product)
            products = self.env['product.product'].browse(product)
            area = products.mrp_area
            invoice_lines.extend([
                (0, 0, {'product_id': product, 'quantity': qty, 'price_unit':jw_id[0].rate if jw_id[0].uom_id.id == products.uom_id.id else (jw_id[0].rate * area),
                        'inno_area': f"{area*qty}", 'inno_price': jw_id[0].rate, 'tax_ids': [(4, tax_id.id)] if tax_id else False,
                        'account_id': journal_id.default_account_id.id})])
            if jw_id[0].incentive > 0:
                fix_inc += (jw_id[0].incentive * (area*qty))
        pen_vals = [self.get_penalty(ptype, penalty_product, journal_id, tax_id) for ptype in ['time_penalty', 'bazaar_penalty', 'qa_penalty', 're_printing', 'cancel']]
        penalty_vals = [(0, 0, val) for val in pen_vals if val.get('price_unit') < 0]
        if penalty_vals:
            invoice_lines.append((0, 0, {'display_type': 'line_section', 'name': 'Penalties'}))
            invoice_lines.extend(penalty_vals)
        incentive = self.get_penalty('incentive', incentive_product, journal_id, tax_id)
        if incentive.get('price_unit') > 0:
            invoice_lines.append((0, 0, {'display_type': 'line_section', 'name': 'Incentive'}))
            invoice_lines.append((0, 0, incentive))
            if fix_inc > 0:
                invoice_lines.append((0, 0, {'quantity': 1, 'price_unit': fix_inc,
                                             'tax_ids': [(4, tax_id.id)] if tax_id else False,
                                             'name': f"Fix Incentive", 'account_id': journal_id.default_account_id.id}))
        if incentive.get('price_unit') <= 0 and fix_inc > 0:
            invoice_lines.append((0, 0, {'display_type': 'line_section', 'name': 'Incentive'}))
            invoice_lines.append((0, 0, {'quantity': 1, 'price_unit': fix_inc,
                                         'tax_ids': [(4, tax_id.id)] if tax_id else False,
                                         'name': f"Fix Incentive", 'account_id': journal_id.default_account_id.id}))
        return invoice_lines

    def get_penalty(self, ptype, penalty_product, journal_id, tax_id):
        model_id = self.env.ref('innorug_manufacture.model_main_jobwork').id
        penalty_records = self.env['inno.incentive.penalty'].search(
            [('type', '=', ptype), ('model_id', '=', model_id), ('rec_id', '=', self.main_jobwork_id.id),
             ('barcode_id', 'in', self.baazar_lines_ids.filtered(lambda bl: bl.state == 'verified').barcode.ids),
             ('rec_id', '=', self.main_jobwork_id.id)])
        pen_amount = sum(penalty_records.mapped('amount'))
        pen_area = sum([product.mrp_area for product in
                        self.env['product.product'].browse(penalty_records.barcode_id.product_id.ids)])
        return {'quantity': 1, 'price_unit': pen_amount if ptype == 'incentive' else -pen_amount, 'inno_area': pen_area,
                'discount': 100 if self._context.get('re_print_discount') and ptype == 're_printing' else 0,
                'name': f"{ptype} on barcodes {penalty_records.barcode_id.mapped('name')}",
                'account_id': journal_id.default_account_id.id, 'tax_ids': [(4, tax_id.id)] if tax_id else False}

    def update_bazaar_status(self):
        bazaars_to_update = self.search([('state', '=', 'receiving'), ('date', '<', fields.Datetime.today())])
        bazaars_to_update.write({'state', '=', 'qc'})
