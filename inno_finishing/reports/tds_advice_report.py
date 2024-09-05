import datetime
from odoo import models, api, _
from odoo.exceptions import UserError, ValidationError, MissingError


class ReportWeavingOrderPaymentAdviceReport(models.AbstractModel):
    _name = 'report.inno_finishing.tds_finishing_payment_advice'
    _description = 'Will Provide the report of all finishing tds advice'

    @api.model
    def _get_report_values(self, docids, data=None):
        sub_data = []
        new_data = {}
        domain = []
        work_orders = False
        move_ids = False
        # vendor_by = self.env['res.partner'].sudo().search([('id', '=', int(data.get('subcontractor_id')))])
        operation_id = self.env['mrp.workcenter'].sudo().search([('id', '=', int(data.get('operation_id')))])
        recs = data.get('records')
        date_from = data.get('from_date')
        subcontractor_id = data.get('subcontractor_id')
        if subcontractor_id:
            domain += [('subcontractor_id','=',int(subcontractor_id))]
        if date_from:
            domain += [('date', '>=', date_from)]
        date_to = data.get('to_date')
        if date_to:
            domain += [('date', '<=', date_to)]
            new_data.update({'to_date': data.get('to_date'),
                             'from_date': data.get('from_date'), 'data': 'yes'})
        work_orders = self.env['finishing.baazar'].sudo().search(domain).filtered(lambda dv: dv.division_id.id
                                                                                             in self.env.user.division_id.ids
                                                                                             and dv.finishing_work_id.operation_id.id == operation_id.id)
        if recs == 'all':
            work_orders = self.env['finishing.baazar'].sudo().search(domain).filtered(lambda dv: dv.division_id.id
                                                                                                 in self.env.user.division_id.ids)
            move_ids = self.env['account.move'].sudo().search([('id', 'in', work_orders.bill_id.ids)])
        else:
            move_ids = self.env['account.move'].sudo().search([ ('id', 'in', work_orders.bill_id.ids)])
        if move_ids:
            self.get_bills(move_ids, sub_data)
        records = self.env['finishing.baazar'].sudo().browse(1)
        if sub_data and work_orders:
            new_data.update(
                {'sub_data': sub_data, 'total_tds_amt': round(sum([rec.get('tds amt') for rec in sub_data]), 2),
                 'total_tds_on_amount': round(sum([rec.get('tds_on_amount') for rec in sub_data]), 2),
                 'division': ', '.join(self.env.user.division_id.mapped('name')) if
                 self.env.user.division_id else 'Main', 'site': 'Main', 'process': operation_id.name})
        return {
            'doc_ids': docids,
            'doc_model': 'finishing.baazar',
            'docs': records,
            'data': new_data, }

    def get_bills(self, move_ids, sub_data):
        vendors = move_ids.partner_id
        for sub in vendors:
            vendor_move = move_ids.filtered(lambda vd: sub.id in vd.partner_id.ids)
            print(vendor_move.finishing_work_id)
            sub_data.append({'pan': sub.pan_no, 'vendor': sub.name if sub else '-',
                             'tds_on_amount': self.calculate_tds_amount(vendor_move),
                             'tds_percent': vendor_move.invoice_line_ids.filtered(
                                 lambda inl: 'TDS Deduction' in inl.name)[0].name.replace("% TDS Deduction", ""),
                             'tds amt': -round(sum([rec.price_total for rec in vendor_move.invoice_line_ids.filtered(
                                 lambda inl: 'TDS Deduction' in inl.name )]), 2)})

    def calculate_tds_amount(self, movs):
        amount = round(sum(mov_ln.price_subtotal for mov_ln in movs.line_ids.filtered(lambda ml: ml.tax_ids)), 2)
        if amount == 0:
            amount = round(sum(mov_ln.price_subtotal for mov_ln in movs.invoice_line_ids.filtered(
                lambda ml: 'Retention Amount' not in ml.name and 'TDS Deduction' not in ml.name)), 2)
        return amount
