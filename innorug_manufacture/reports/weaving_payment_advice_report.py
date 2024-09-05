import datetime
from odoo import models, api, _
from odoo.exceptions import UserError, ValidationError, MissingError


class ReportWeavingOrderPaymentAdviceReport(models.AbstractModel):
    _name = 'report.innorug_manufacture.weaving_payment_advice'
    _description = 'Will Provide the report of all weaving payment advice'

    @api.model
    def _get_report_values(self, docids, data=None):
        sub_data = []
        new_data = {}
        domain = []
        work_orders = False
        vendor_by = self.env['res.partner'].sudo().search([('id', '=', int(data.get('subcontractor_id')))])
        order_by = self.env['main.jobwork'].sudo().search([('id', '=', int(data.get('order_no')))])
        baazar_by = self.env['main.baazar'].sudo().search([('id', '=', int(data.get('receive_no')))])
        branch_id = self.env['weaving.branch'].sudo().search([('id', '=', int(data.get('branch_id')))])
        if baazar_by:
            work_orders = baazar_by
        elif order_by:
            date_from = data.get('from_date')
            if date_from:
                domain += [('date', '>=', date_from)]
            date_to = data.get('to_date')
            if date_to:
                domain += [('date', '<=', date_to)]
                new_data.update({'to_date': data.get('to_date'),
                                 'from_date': data.get('from_date'), 'data': 'yes'})
            domain += [('main_jobwork_id', '=', order_by.id)]
            work_orders = self.env['main.baazar'].sudo().search(domain)
        elif vendor_by:
            date_from = data.get('from_date')
            if date_from:
                domain += [('date', '>=', date_from)]
            date_to = data.get('to_date')
            if date_to:
                domain += [('date', '<=', date_to)]
                new_data.update({'to_date': data.get('to_date'),
                                 'from_date': data.get('from_date'), 'data': 'yes'})
            domain += [('subcontractor_id', '=', vendor_by.id)]
            work_orders = self.env['main.baazar'].sudo().search(domain)
        else:
            date_from = data.get('from_date')
            if date_from:
                domain += [('date', '>=', date_from)]
            date_to = data.get('to_date')
            if date_to:
                domain += [('date', '<=', date_to)]
                new_data.update({'to_date': data.get('to_date'),
                                 'from_date': data.get('from_date'), 'data': 'yes'})
                work_orders = self.env['main.baazar'].sudo().search(domain)
        move_ids = False
        if not self.env.user.division_id:
            raise UserError(_("Please ask your admin to set divisions"))
        else:
            if work_orders:
                brnch_order = work_orders
                is_branch = data.get('include_branch')
                exclude_branch = data.get('exclude_branch')
                if not is_branch:
                    work_orders = work_orders.filtered(
                        lambda bl: not bl.main_jobwork_id.is_branch_subcontracting and not bl.main_jobwork_id.branch_id)
                elif exclude_branch:
                    work_orders = brnch_order.filtered(
                        lambda bl: bl.main_jobwork_id.branch_id)
                if branch_id:
                    work_orders = brnch_order.filtered(
                        lambda bl: branch_id.id in bl.main_jobwork_id.branch_id.ids)
                move_ids = self.env['account.move'].sudo().search([]).filtered(
                    lambda bz: bz.payment_state == data.get(
                        'payment_state') and bz.bazaar_id.id in work_orders.filtered(
                        lambda dv: dv.division_id.id in self.env.user.division_id.ids).ids)
            if not move_ids:
                raise UserError(_("Job work not found"))
        if data.get('gst') == 'registered':
            move_ids = move_ids.filtered(lambda sb: sb.partner_id.vat)
            new_data.update({'gst': 'yes', 'header': 'Weaving Payment Advice (Registered)'})
        elif data.get('gst') == 'unregistered':
            move_ids = move_ids.filtered(lambda sb: not sb.partner_id.vat)
            new_data.update({'gst': 'no', 'header': 'Weaving Payment Advice (Unregistered)'})
        else:
            new_data.update({'gst': 'yes', 'header': 'Weaving Payment Advice'})
        if work_orders and data.get('report_type') == 'weaving_payment_advice':
            self.get_bills(move_ids, sub_data)
        records = self.env['main.baazar'].sudo().browse(1)
        payment_state = {'not_paid': 'Not Paid',
                         'in_payment': 'In Payment',
                         'paid': 'Paid',
                         'partial': 'Partially Paid',
                         'reversed': 'Reversed',
                         'invoicing_legacy': 'Invoicing App Legacy', }
        if sub_data and work_orders and move_ids:
            new_data.update(
                {'sub_data': sub_data, 'checked_amt': f"₹{round(sum([rec.amount_untaxed for rec in move_ids]), 4)}",
                 'division': ', '.join(self.env.user.division_id.mapped('name')) if
                 self.env.user.division_id else 'Main', 'site': 'Main',
                 'net_amount': f"₹{round(sum([rec.amount_total for rec in move_ids]), 4)}",
                 'paid': f"₹{self.get_paid_amoun(move_ids)}",
                 'payment_state': payment_state.get(data.get('payment_state')),
                 'amount_dues': f"₹{round(sum([rec.amount_residual for rec in move_ids]), 4)}",
                 'GST': f"₹{round(self.get_gst_record(move_ids), 2)}", 'summary': self.get_summary_amount(move_ids), })
        return {
            'doc_ids': docids,
            'doc_model': 'finishing.work.order',
            'docs': records,
            'data': new_data, }

    def get_summary_amount(self, move_ids):
        bazar = move_ids.bazaar_id
        lines = bazar.baazar_lines_ids.filtered(lambda ln: ln.state == 'verified')
        total_area = sum([rec.product_id.mrp_area for rec in lines])
        amount = sum([rec.job_work_id.rate * rec.product_id.mrp_area for rec in lines])
        fixed_incentive = sum([rec.job_work_id.incentive * rec.product_id.mrp_area for rec in lines])
        penality = -sum([rec.penalty for rec in lines])
        retention = sum([rec.price_subtotal for rec in
                         move_ids.invoice_line_ids.filtered(lambda inv: 'Retention Amount' in inv.name)])
        tds = sum(
            [rec.price_subtotal for rec in move_ids.invoice_line_ids.filtered(lambda inv: 'TDS Deduction' in inv.name)])
        deduction = retention + penality + tds
        total_amount = (amount + fixed_incentive) + deduction
        new_data = {'gross_amount': round(amount, 2), 'Fixed Incentive': round(fixed_incentive, 2),
                    'penality': round(penality, 2), 'retention': round(retention, 2), 'tds': round(tds, 2),
                    'payble': f"₹{round(total_amount, 2)}", 'area': f"{round(total_area, 4)} Sq. Yard", 'pcs': f"{len(lines)} PCS"}
        return new_data

    def get_bills(self, move_ids, sub_data):
        vendors = move_ids.partner_id
        for sub in vendors:
            vendor_move = move_ids.filtered(lambda vd: sub.id in vd.partner_id.ids)
            sub_data.append({'vendors': f"{sub.name} ({sub.id})", 'GSTIN': sub.vat if sub.vat else '-',
                             'checked_amt': f"₹{round(sum([rec.amount_untaxed for rec in vendor_move]), 2)}",
                             'net_amount': f"₹{round(sum([rec.amount_total for rec in vendor_move]), 2)}",
                             'paid': f"₹{self.get_paid_amoun(vendor_move)}",
                             'GST': f"₹{round(self.get_gst_record(vendor_move), 2)}",
                             'amount_dues': f"₹{round(sum([rec.amount_residual for rec in vendor_move]), 2)}",
                             'bills': [
                                 {'bill_no': ac.name, 'receive_no': f"{ac.bazaar_id.reference}",
                                  'receive_date': ac.invoice_date.strftime('%d/%m/%Y') if ac.invoice_date else False,
                                  'order_no': ac.bazaar_id.main_jobwork_id.reference,
                                  'gross_amount': round(ac.tax_totals.get('amount_untaxed'), 2),
                                  'GST': str(self.gst_details(ac)),
                                  'net_amount': round(ac.tax_totals.get('amount_total'),2), 'amount_due': ac.amount_residual,
                                  'amount_paid': self.get_paid_amount(ac)
                                  } for ac in
                                 vendor_move]})

    def get_gst_record(self, vendor_move):
        amount = 0.0
        if vendor_move:
            for rec in vendor_move:
                if rec.tax_totals.get('groups_by_subtotal').get('Untaxed Amount'):
                    for line in rec.tax_totals.get('groups_by_subtotal').get('Untaxed Amount'):
                        amount += line.get('tax_group_amount')
            return amount

    def get_paid_amoun(self, vendor_move):
        amount = 0.0
        if vendor_move:
            for rec in vendor_move:
                if rec.invoice_payments_widget:
                    for line in rec.invoice_payments_widget.get('content'):
                        amount += line.get('amount')
            return amount
        return 0

    def get_total_area(self, ac):
        area = 0.0
        for rec in ac.invoice_line_ids:
            if rec.product_id:
                area += rec.product_id.mrp_area * rec.quantity
        return round(area, 4)

    def get_paid_amount(self, ac):
        amount = 0.0
        if ac.invoice_payments_widget:
            for rec in ac.invoice_payments_widget.get('content'):
                amount += rec.get('amount')
        return amount

    def gst_details(self, records):
        amount = 0.0
        if records.tax_totals.get('groups_by_subtotal').get('Untaxed Amount'):
            for rec in records.tax_totals.get('groups_by_subtotal').get('Untaxed Amount'):
                amount += rec.get('tax_group_amount')
        return amount
