import datetime
from odoo import models, api, _
from odoo.exceptions import UserError, ValidationError, MissingError


class ReportFinishingpayments(models.AbstractModel):
    _name = 'report.inno_finishing.finishing_payment_advice'
    _description = 'Will Provide the report of all finishing payment advice'

    @api.model
    def _get_report_values(self, docids, data=None):
        sub_data = []
        new_data = {}
        domain = []
        work_orders = False
        vendor_by = self.env['res.partner'].sudo().search([('id', '=', int(data.get('subcontractor_id')))])
        order_by = self.env['finishing.work.order'].sudo().search([('id', '=', int(data.get('order_no')))])
        baazar_by = self.env['finishing.baazar'].sudo().search([('id', '=', int(data.get('receive_no')))])
        operation_id = self.env['mrp.workcenter'].sudo().search([('id', '=', int(data.get('operation')))])
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
            domain += [('finishing_work_id', '=', order_by.id)]
            work_orders = self.env['finishing.baazar'].sudo().search(domain)
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
            work_orders = self.env['finishing.baazar'].sudo().search(domain)
        else:
            date_from = data.get('from_date')
            if date_from:
                domain += [('date', '>=', date_from)]
            date_to = data.get('to_date')
            if date_to:
                domain += [('date', '<=', date_to)]
                new_data.update({'to_date': data.get('to_date'),
                                 'from_date': data.get('from_date'), 'data': 'yes'})
                work_orders = self.env['finishing.baazar'].sudo().search(domain).filtered( lambda dv: dv.division_id.id
                                                                                                      in self.env.user.division_id.ids
                                                                                                      and dv.finishing_work_id.operation_id.id == operation_id.id)
        move_ids = False
        if not self.env.user.division_id:
            raise UserError(_("Please ask your admin to set divisions"))
        else:
            if work_orders:
                # bill_id
                # move_ids = self.env['account.move'].sudo().search([]).filtered(
                #     lambda bz: bz.finishing_work_id.id in work_orders.filtered(
                #         lambda dv: dv.division_id.id in self.env.user.division_id.ids and bz.payment_state == data.get(
                #             'payment_state') and dv.finishing_work_id.operation_id.id == operation_id.id).finishing_work_id.ids)

                move_ids = self.env['account.move'].sudo().search([('payment_state','=',data.get(
                        'payment_state')),('id','in', work_orders.bill_id.ids)])
            if not move_ids:
                raise UserError(_("Job work not found"))
        if data.get('gst') == 'registered':
            move_ids = move_ids.filtered(lambda sb: sb.partner_id.vat)
            new_data.update({'gst': 'yes', 'header': f'{operation_id.name} Payment Advice (Registered)'})
        elif data.get('gst') == 'unregistered':
            move_ids = move_ids.filtered(lambda sb: not sb.partner_id.vat)
            new_data.update({'gst': 'no', 'header': f'{operation_id.name} Payment Advice (Unregistered)'})
        else:
            new_data.update({'gst': 'yes', 'header': f'{operation_id.name} Payment Advice'})
        if work_orders and data.get('report_type') == 'payment_advice':
            self.get_bills(move_ids, sub_data)
        records = self.env['finishing.baazar'].sudo().browse(1)
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
        # bazar = move_ids.finishing_bazaar_id
        unit = {'sq_yard': 'Sq. Yard',
                'feet': 'Feet',
                'sq_feet': 'Sq. Feet',
                'choti': 'Sq. Meter', }
        bazar=self.env['finishing.baazar'].sudo().search([('bill_id', 'in', move_ids.ids)])
        lines = bazar.jobwork_received_ids.filtered(lambda ln: ln.state == 'verified')
        total_area = sum([rec.total_area for rec in lines])
        amount = sum([rec.rate * rec.total_area for rec in lines])
        fixed_incentive = sum([(rec.fixed_incentive * rec.total_area) + rec.incentive for rec in lines])
        penality = -sum([rec.penalty for rec in lines])
        tds = sum(
            [rec.price_subtotal for rec in move_ids.invoice_line_ids.filtered(lambda inv: 'TDS Deduction' in inv.name)])
        fright_issue = sum(
            [rec.price_subtotal for rec in
             move_ids.invoice_line_ids.filtered(lambda inv: 'Freight Issue Amount for' in inv.name)])
        fright_receive = sum(
            [rec.price_subtotal for rec in
             move_ids.invoice_line_ids.filtered(lambda inv: 'Freight Receive Amount for' in inv.name)])
        deduction = penality + tds + fright_issue + fright_receive
        total_amount = (amount + fixed_incentive) + deduction
        new_data = {'gross_amount': round(amount, 2), 'Fixed Incentive': round(fixed_incentive, 2),
                    'penality': round(penality, 2), 'retention': 0, 'tds': round(tds, 2),
                    'frieght_iss': round(fright_issue, 2), 'frieght_rc': round(fright_receive, 2),
                    'payble': f"₹{round(total_amount, 2)}", 'area': f"{round(total_area, 4)} {unit.get(bazar.jobwork_received_ids[0].unit)}",
                    'pcs': f"{len(lines)} PCS"}
        return new_data

    def get_bills(self, move_ids, sub_data):
        vendors =sorted(move_ids.partner_id)
        for sub in vendors:
            vendor_move = move_ids.filtered(lambda vd: sub.id in vd.partner_id.ids)
            sub_data.append({'vendors': f"{sub.name} ({sub.id})", 'GSTIN': sub.vat if sub.vat else '-',
                             'checked_amt': f"₹{round(sum([rec.amount_untaxed for rec in vendor_move]), 2)}",
                             'net_amount': f"₹{round(sum([rec.amount_total for rec in vendor_move]), 2)}",
                             'paid': f"₹{self.get_paid_amoun(vendor_move)}",
                             'GST': f"₹{round(self.get_gst_record(vendor_move), 2)}",
                             'amount_dues': f"₹{round(sum([rec.amount_residual for rec in vendor_move]), 2)}",
                             'bills': [
                                 {'bill_no': ac.name, 'receive_no':', '.join([f"{rec.reference} - {rec.date.strftime('%d/%m/%Y') if rec.date else False}" for rec in self.env['finishing.baazar'].sudo().search([('bill_id', '=', ac.id)])]),
                                  'receive_date': ac.invoice_date.strftime('%d/%m/%Y') if ac.invoice_date else False,
                                  'order_no': ac.finishing_work_id.name,
                                  'gross_amount': round(ac.tax_totals.get('amount_untaxed'), 2),
                                  'GST': str(self.gst_details(ac)),
                                  'net_amount': round(ac.tax_totals.get('amount_total'), 2),
                                  'amount_due': ac.amount_residual,
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

    #
    # def get_total_area(self, ac):
    #     area = 0.0
    #     for rec in ac.invoice_line_ids:
    #         if rec.product_id:
    #             area += rec.product_id.mrp_area * rec.quantity
    #     return round(area, 4)

    def get_paid_amount(self, ac):
        amount = 0.0
        if ac.invoice_payments_widget:
            for rec in ac.invoice_payments_widget.get('content'):
                amount += rec.get('amount')
        return round(amount,3)

    def gst_details(self, records):
        amount = 0.0
        if records.tax_totals.get('groups_by_subtotal').get('Untaxed Amount'):
            for rec in records.tax_totals.get('groups_by_subtotal').get('Untaxed Amount'):
                amount += rec.get('tax_group_amount')
        return amount
