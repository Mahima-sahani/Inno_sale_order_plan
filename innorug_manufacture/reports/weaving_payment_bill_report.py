import datetime
from odoo import models, api, _
from odoo.exceptions import UserError, ValidationError, MissingError


class ReportWeavingOrderBalanceReport(models.AbstractModel):
    _name = 'report.innorug_manufacture.weaving_payment_bills'
    _description = 'Will Provide the report of all weaving payment bill'

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
                    lambda bz: bz.payment_state == data.get('payment_state') and bz.bazaar_id.id in work_orders.filtered(
                        lambda dv: dv.division_id.id in self.env.user.division_id.ids).ids)
            if not move_ids:
                raise UserError(_("Job work not found"))
        if data.get('gst') == 'registered':
            move_ids = move_ids.filtered(lambda sb: sb.partner_id.vat)
            new_data.update({'gst': 'yes', 'header': 'Weaving Bill (Registered)'})
        elif data.get('gst') == 'unregistered':
            move_ids = move_ids.filtered(lambda sb: not sb.partner_id.vat)
            new_data.update({'gst': 'no', 'header': 'Weaving Bill (Unregistered)'})
        else:
            new_data.update({'gst': 'yes', 'header': 'Weaving Bill'})
        if work_orders and data.get('report_type') == 'weaving_bills':
            self.get_bills(move_ids, sub_data)
        records = self.env['main.baazar'].sudo().browse(1)
        if sub_data and work_orders:
            new_data.update({'sub_data': sub_data,'division': ', '.join(self.env.user.division_id.mapped('name')) if
                 self.env.user.division_id else 'Main','site': 'Main',})
        return {
            'doc_ids': docids,
            'doc_model': 'finishing.work.order',
            'docs': records,
            'data': new_data, }

    def get_bills(self, move_ids, sub_data):
        vendors = move_ids.partner_id
        for sub in vendors:
            vendor_move = move_ids.filtered(lambda vd: sub.id in vd.partner_id.ids)
            sub_data.append({'bill': [
                {'receive_no': f"{ac.bazaar_id.reference}", 'invoice_gst': self.gst_details(ac), 'invoice_amount':self.gst_invoice_amount(ac),
                 'vendor': f"{sub.name} ({sub.id})",
                 'GSTIN': sub.vat if sub.vat else '-', 'order_no': ac.bazaar_id.main_jobwork_id.reference,
                 'bill_date': ac.invoice_date.strftime('%d/%m/%Y') if ac.invoice_date else False,
                 'order_date': ac.bazaar_id.main_jobwork_id.issue_date,
                 'total_qty': sum(ac.invoice_line_ids.filtered(lambda pd: pd.product_id).mapped('quantity')),
                 'total_area': self.get_total_area(ac)
                    , 'bill_no': ac.name, 'gross_amout': round(ac.amount_untaxed, 2), 'untax_amout': round(sum(mov_ln.price_subtotal for mov_ln in ac.line_ids.filtered(lambda ml: ml.tax_ids)), 2)
                    , 'amount_in_words': ac.amount_total_words,
                 'is_tax': 'yes' if ac.invoice_line_ids.tax_ids else 'no',
                 'gross_amount': ac.tax_totals.get('formatted_amount_total'), 'amount_due': f"₹{ac.amount_residual}",
                                  'amount_paid': self.get_paid_amount(ac)
                    , 'lines': [{'product': line.product_id.default_code if line.product_id else line.name,
                                 'quality': line.product_id.product_tmpl_id.quality.name if line.product_id else False,
                                 'area': line.inno_area if line.product_id else False,
                                 'rate':round(line.price_subtotal/self.get_total_area_per_line(line),2) if line.product_id else False,
                                 'pcs': line.quantity if line.product_id else False, 'unit_price': line.price_unit,
                                 'taxes': ', '.join(line.tax_ids.mapped('name')), 'total_amount': line.price_subtotal
                                 } for line in ac.invoice_line_ids if not line.price_subtotal == 0.0]} for ac in
                vendor_move]})

    def get_paid_amount(self, ac):
        data = {}
        if ac.invoice_payments_widget:
            for rec in ac.invoice_payments_widget.get('content'):
                data.update({f"Paid on {rec.get('date')}" : f"{rec.get('amount_company_currency')}"})
        return data

    def get_total_area(self, ac):
        area = 0.0
        for rec in ac.invoice_line_ids:
            if rec.product_id:
                area += rec.product_id.mrp_area * rec.quantity
        return round(area, 4)

    def get_total_area_per_line(self, line):
        area = 0.0
        for rec in line:
            if rec.product_id:
                area += rec.product_id.mrp_area * rec.quantity
        return round(area, 4) if area >0.0 else 1

    def gst_details(self, records):
        invoice_gst = {}
        if records.tax_totals.get('groups_by_subtotal').get('Untaxed Amount'):
            for rec in records.tax_totals.get('groups_by_subtotal').get('Untaxed Amount'):
                invoice_gst.update({rec.get('tax_group_name'): rec.get('tax_group_amount')})
        return invoice_gst

    def gst_invoice_amount(self,records):
        amount=0.0
        if records.tax_totals.get('groups_by_subtotal').get('Untaxed Amount'):
            for rec in records.tax_totals.get('groups_by_subtotal').get('Untaxed Amount'):
                amount += rec.get('tax_group_amount')
            amount += round(sum(mov_ln.price_subtotal for mov_ln in records.line_ids.filtered(lambda ml: ml.tax_ids)), 2)
        return amount
