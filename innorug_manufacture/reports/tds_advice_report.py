import datetime
from odoo import models, api, _
from odoo.exceptions import UserError, ValidationError, MissingError


class ReportWeavingOrderPaymentAdviceReport(models.AbstractModel):
    _name = 'report.innorug_manufacture.tds_payment_advice'
    _description = 'Will Provide the report of all weaving payment advice'

    @api.model
    def _get_report_values(self, docids, data=None):
        sub_data = []
        new_data = {}
        domain = []
        work_orders = False
        move_ids = False
        # vendor_by = self.env['res.partner'].sudo().search([('id', '=', int(data.get('subcontractor_id')))])
        branch_id = self.env['weaving.branch'].sudo().search([('id', '=', int(data.get('branch_id')))])
        # is_branch = data.get('include_branch')
        exclude_branch = data.get('exclude_branch')
        date_from = data.get('from_date')
        if date_from:
            domain += [('date', '>=', date_from)]
        date_to = data.get('to_date')
        if date_to:
            domain += [('date', '<=', date_to)]
            new_data.update({'to_date': data.get('to_date'),
                             'from_date': data.get('from_date'), 'data': 'yes'})
        work_orders = self.env['main.baazar'].sudo().search(domain)
        if work_orders:
            move_ids = self.env['account.move'].sudo().search([]).filtered(
                lambda bz: bz.payment_state in ['not_paid', 'in_payment',
                                                'partial'] and bz.bazaar_id.id in work_orders.filtered(
                    lambda dv: dv.division_id.id in self.env.user.division_id.ids).ids)
            if branch_id:
                move_ids = move_ids.filtered(lambda mv: branch_id.id in  mv.job_work_id.branch_id.ids)
            if exclude_branch:
                move_ids = move_ids.filtered(lambda mv: not mv.job_work_id.branch_id)
            if move_ids:
                self.get_bills(move_ids, sub_data)
        records = self.env['main.baazar'].sudo().browse(1)
        if sub_data and work_orders:
            new_data.update(
                {'sub_data': sub_data, 'total_tds_amt': round(sum([rec.get('tds amt') for rec in sub_data]), 2),
                 'total_tds_on_amount': round(sum([rec.get('tds_on_amount') for rec in sub_data]), 2),
                 'division': ', '.join(self.env.user.division_id.mapped('name')) if
                 self.env.user.division_id else 'Main', 'site': 'Main', 'process': 'Weaving'})
        return {
            'doc_ids': docids,
            'doc_model': 'finishing.work.order',
            'docs': records,
            'data': new_data, }

    def get_bills(self, move_ids, sub_data):
        vendors = move_ids.partner_id
        for sub in vendors:
            vendor_move = move_ids.filtered(lambda vd: sub.id in vd.partner_id.ids)
            sub_data.append({'pan': sub.pan_no, 'vendor': sub.name if sub else '-',
                             'tds_on_amount': self.calculate_tds_amount(vendor_move),
                             'tds_percent': vendor_move.invoice_line_ids.filtered(
                                 lambda inl: 'TDS Deduction' in inl.name)[0].name.replace("% TDS Deduction", ""),
                             'tds amt': -round(sum([rec.price_total for rec in vendor_move.invoice_line_ids.filtered(
                                 lambda inl: 'TDS Deduction' in inl.name)]), 2)})

    def calculate_tds_amount(self, movs):
        amount = round(sum(mov_ln.price_subtotal for mov_ln in movs.line_ids.filtered(lambda ml: ml.tax_ids)), 2)
        if amount == 0:
            amount = round(sum(mov_ln.price_subtotal for mov_ln in movs.invoice_line_ids.filtered(
                lambda ml: 'Retention Amount' not in ml.name and 'TDS Deduction' not in ml.name)), 2)
        return amount
