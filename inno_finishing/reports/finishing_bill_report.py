from odoo import models, api, _
from odoo.exceptions import UserError, ValidationError, MissingError


class ReportFinishingBillReport(models.AbstractModel):
    _name = 'report.inno_finishing.finishing_payment_bills'
    _description = 'Will Provide the report of all finishing payment bill'

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
                work_orders =self.env['finishing.baazar'].sudo().search(domain).filtered( lambda dv: dv.division_id.id
                                                                                                      in self.env.user.division_id.ids
                                                                                                      and dv.finishing_work_id.operation_id.id == operation_id.id)
        move_ids = False
        if not self.env.user.division_id:
            raise UserError(_("Please ask your admin to set divisions"))
        else:
            if work_orders:
                # move_ids = self.env['account.move'].sudo().search([]).filtered(
                #     lambda bz: bz.finishing_work_id.id in work_orders.filtered(
                #         lambda dv: dv.division_id.id in self.env.user.division_id.ids and bz.payment_state == data.get(
                #             'payment_state') and dv.finishing_work_id.operation_id.id == operation_id.id).finishing_work_id.ids)
                move_ids = self.env['account.move'].sudo().search([('payment_state', '=', data.get(
                    'payment_state')), ('id', 'in', work_orders.bill_id.ids)])
            if not move_ids:
                raise UserError(_("Job work not found"))
        if data.get('gst') == 'registered':
            move_ids = move_ids.filtered(lambda sb: sb.partner_id.vat)
            new_data.update({'gst': 'yes', 'header': f"{operation_id.name} Bill (Registered)"})
        elif data.get('gst') == 'unregistered':
            move_ids = move_ids.filtered(lambda sb: not sb.partner_id.vat)
            new_data.update({'gst': 'no', 'header': f"{operation_id.name} Bill (Unregistered)"})
        else:
            new_data.update({'gst': 'yes', 'header': f"{operation_id.name} Bill"})
        if work_orders and data.get('report_type') == 'payment_bill':
            self.get_bills(move_ids, sub_data)
        records = self.env['finishing.baazar'].sudo().browse(1)
        if sub_data and work_orders:
            new_data.update({'sub_data': sub_data, 'division': ', '.join(self.env.user.division_id.mapped('name')) if
            self.env.user.division_id else 'Main', 'site': 'Main', })
        return {
            'doc_ids': docids,
            'doc_model': 'finishing.work.order',
            'docs': records,
            'data': new_data, }

    def get_bills(self, move_ids, sub_data):
        vendors = sorted(move_ids.partner_id)
        for sub in vendors:
            vendor_move = move_ids.filtered(lambda vd: sub.id in vd.partner_id.ids)
            sub_data.append({'bill': [
                {'receive_no': ', '.join(
                    self.env['finishing.baazar'].sudo().search([('bill_id', '=', ac.id)]).mapped('reference')),
                    'invoice_gst': self.gst_details(ac),
                    'vendor': f"{sub.name} ({sub.id})",
                    'GSTIN': sub.vat if sub.vat else '-', 'order_no': ac.finishing_work_id.name,
                    'bill_date': ac.invoice_date.strftime('%d/%m/%Y') if ac.invoice_date else False,
                    'order_date': ac.finishing_bazaar_id.finishing_work_id.issue_date,
                    'total_qty': sum(ac.invoice_line_ids.filtered(lambda pd: pd.product_id).mapped('quantity')),
                    'total_area': self.get_total_area(ac)
                    , 'bill_no': ac.name, 'gross_amout': round(ac.amount_untaxed, 2), 'untax_amout': round(
                    sum(mov_ln.price_subtotal for mov_ln in ac.line_ids.filtered(lambda ml: ml.tax_ids)), 2)
                    , 'amount_in_words': ac.amount_total_words,
                    'is_tax': 'yes' if ac.invoice_line_ids.tax_ids else 'no',
                    'gross_amount': ac.tax_totals.get('formatted_amount_total'), 'amount_due': f"₹{ac.amount_residual}",
                    'amount_paid': self.get_paid_amount(ac)
                    , 'lines': [{'product': line.product_id.default_code if line.product_id else line.name,
                                 'quality': line.product_id.product_tmpl_id.quality.name if line.product_id else False,
                                 'area': line.inno_area if line.product_id else False,
                                 'pcs': line.quantity if line.product_id else False, 'unit_price': line.price_unit,
                                 'taxes': ', '.join(line.tax_ids.mapped('name')), 'total_amount': line.price_subtotal
                                 } for line in ac.invoice_line_ids if not line.price_subtotal == 0.0]} for ac in
                vendor_move]})

    def get_paid_amount(self, ac):
        data = {}
        if ac.invoice_payments_widget:
            for rec in ac.invoice_payments_widget.get('content'):
                data.update({f"Paid on {rec.get('date')}": f"{rec.get('amount_company_currency')}"})
        return data

    def get_total_area(self, ac):
        area = 0.0
        unit = {'sq_yard': 'Sq. Yard',
                'feet': 'Feet',
                'sq_feet': 'Sq. Feet',
                'choti': 'Sq. Meter', }
        bazar_ids = self.env['finishing.baazar'].sudo().search([('bill_id','=',ac.id)])
        if bazar_ids:
            for rec in bazar_ids.jobwork_received_ids.filtered(lambda jr: jr.state == 'verified'):
                area += rec.total_area
            return f"{round(area, 4)} {unit.get(bazar_ids.jobwork_received_ids[0].unit)}"
        return 0.0

    def gst_details(self, records):
        invoice_gst = {}
        if records.tax_totals.get('groups_by_subtotal').get('Untaxed Amount'):
            for rec in records.tax_totals.get('groups_by_subtotal').get('Untaxed Amount'):
                invoice_gst.update({rec.get('tax_group_name'): rec.get('tax_group_amount')})
        return invoice_gst
