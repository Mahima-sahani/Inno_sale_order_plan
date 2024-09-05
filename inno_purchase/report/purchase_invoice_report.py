import datetime
from odoo import models, api, _
from odoo.exceptions import UserError, ValidationError, MissingError


class ReportPurchaseInvoicw(models.AbstractModel):
    _name = 'report.inno_purchase.report_purchase_invoice'
    _description = 'Will Provide the report worker wise outstanding reports'

    @api.model
    def _get_report_values(self, docids, data=None):

        new_data = {}
        tax_data = {}
        records = self.env['inno.receive'].sudo().browse(docids)
        if records.types in ['tufting_cloth_weaving', 'third_backing_cloth']:
            sub_data = [
                {'product': rec.product_id.default_code if rec.product_id else rec.label,
                 'hsn': rec.product_id.l10n_in_hsn_code or 'N/A', 'indent': '',
                 'qty': rec.receive_qty if rec.deal_uom_id.id not in rec.uom_id.ids and rec.product_id and rec.deal_uom_id else rec.invoice_qty,
                 'unit': rec.deal_uom_id.name, 'deal_qty': rec.invoice_qty if rec.product_id else 0,
                 'types': records.types,
                 'deal_unit': rec.deal_uom_id.name, 'discount': rec.discount,
                 'rate': rec.rate, 'amont': rec.price_subtotal, 'remark': rec.remarks,
                 'gst': ', '.join(rec.tax_id.mapped('name')), } for rec in records.inno_receive_line]
        else:
            sub_data = [
                {'product': rec.product_id.default_code if rec.product_id else rec.label,
                 'hsn': rec.product_id.l10n_in_hsn_code or 'N/A', 'indent': '',
                 'qty': rec.receive_qty if rec.deal_uom_id.id not in rec.uom_id.ids and rec.product_id and rec.deal_uom_id else rec.invoice_qty,
                 'unit': rec.uom_id.name, 'deal_qty': round(rec.invoice_qty,2) if rec.product_id else 0,
                 'types': records.types,
                 'deal_unit': rec.deal_uom_id.name, 'discount': rec.discount,
                 'rate': rec.rate, 'amont': rec.price_subtotal, 'remark': rec.remarks,
                 'gst': ', '.join(rec.tax_id.mapped('name')), } for rec in records.inno_receive_line]
        bill_id = self.env['account.move'].sudo().search(
            [('receive_id', '=', records.id), ('move_type', '=', 'in_invoice')])
        bill_refund_id = self.env['account.move'].sudo().search(
            [('receive_id', '=', records.id), ('move_type', '=', 'in_refund')])
        if bill_refund_id:
            payble = float(bill_id.tax_totals.get('amount_total_rounded') if bill_id.tax_totals.get(
                'formatted_amount_total_rounded') else records.tax_totals.get(
                'amount_total')) - float(bill_refund_id.tax_totals.get('amount_total_rounded') if bill_refund_id.tax_totals.get(
                'amount_total_rounded') else bill_refund_id.tax_totals.get('amount_total'))
            tax_data.update({ 'bill_refund_id': round(bill_refund_id.tax_totals.get('amount_total_rounded'),2) if bill_refund_id.tax_totals.get(
                 'amount_total_rounded') else round(bill_refund_id.tax_totals.get('amount_total'),2)})
        else:
            payble = float(bill_id.tax_totals.get('amount_total_rounded') if bill_id.tax_totals.get(
                'formatted_amount_total_rounded') else records.tax_totals.get(
                'amount_total'))
        tax_data.update(
            {'untax_amout': round(records.tax_totals.get('amount_untaxed'), 2),
             'amount_in_words': records.currency_id.amount_to_text(payble),
             'net_payable': round(payble,3),
             'DESC': ', '.join(
                records.inno_receive_line.tax_id.mapped('name')) if records.inno_receive_line.tax_id else 'GST 0%',
             'rounding_amount': bill_id.tax_totals.get('rounding_amount'),
             'Taxable': round(records.tax_totals.get('amount_untaxed'), 2)})

        invoice_gst = {}
        total_tax = []
        if records.tax_totals.get('groups_by_subtotal').get('Untaxed Amount'):
            tax_data.update({'tax': 'yes'})
            for rec in records.tax_totals.get('groups_by_subtotal').get('Untaxed Amount'):
                invoice_gst.update({rec.get('tax_group_name'): round(rec.get('tax_group_amount'), 2)})

                total_tax.append(round(rec.get('tax_group_amount'), 2))
        else:
            tax_data.update({'tax': 'no'})

        sale_tax = tax_data.get('untax_amout')
        gst = sum(total_tax)
        net_amt = sale_tax + gst

        tax_data['gross_amount'] = net_amt
        if tax_data.get('bill_refund_id'):
            debit_amt = tax_data.get('bill_refund_id')
            net_pay = net_amt-debit_amt
            tax_data['net_payable'] = net_pay
            tax_data['amount_in_words'] = records.currency_id.amount_to_text(net_pay)


        if records:
            new_data.update({'cloth': "no", })
            if records.inno_purchase_id.types == 'yarn':
                new_data.update({'header': "Yarn Purchase Invoice", })
            if records.inno_purchase_id.types == 'wool':
                new_data.update({'header': "Wool Purchase Invoice", })
            if records.inno_purchase_id.types == 'purchase':
                new_data.update({'header': "Purchase Invoice", })
            if records.types == 'tufting_cloth_weaving':
                new_data.update({'header': "TUFTING CLOTH WEAVING INVOICE",'cloth': "yes" })
            if records.types == 'newar_production':
                new_data.update({'header': "NEWAR PRODUCTION INVOICE", })
            if records.types == 'tana_job_order':
                new_data.update({'header': "TANA JOB WORKER INVOICE", })
            if records.types == 'third_backing_cloth':
                new_data.update({'header': "THIRD BACKING CLOTH INVOICE", 'cloth': "yes"})
            if records.types == 'spinning':
                new_data.update({'header': "SPINNING JOB WORKER INVOICE", })
            new_data.update({'supplier': records.inno_purchase_id.subcontractor_id.name, 'types': records.types,
                             'code': records.inno_purchase_id.subcontractor_id.name,
                             "address": records.inno_purchase_id.subcontractor_id.street,
                             'mobile': '' if records.inno_purchase_id.subcontractor_id.mobile == 'NULL' else records.inno_purchase_id.subcontractor_id.mobile,
                             'gstin': records.inno_purchase_id.subcontractor_id.vat,
                             'Supplier Doc Date': records.supplier_invoice_date.strftime(
                                 '%d/%m/%Y') if records.supplier_invoice_date else False, 'doc': bill_id.name,
                             'challan': records.reference,
                             'ref_doc': records.inno_purchase_id.reference, 'docDate': records.date.strftime('%d/%m/%Y') if records.date else False,
                             'Received_By': self.env.user.name, 'Godown': records.location.warehouse_id.name,
                             'Supplier Doc': records.receive_invoice,
                             'Supplier Date': records.date.strftime('%d/%m/%Y') if records.date else False,
                             'Invoice Date': records.invoice_date.strftime('%d/%m/%Y') if records.invoice_date else False,
                             'receipt': records.receipt_no})
        new_data.update({'sub_data': sub_data, 'tax_data': tax_data, 'invoice_gst': invoice_gst,
                         'deal_qty': round(sum([rec.get('deal_qty') for rec in sub_data]),2),
                         'total_amount': round(sum([rec.get('amont') for rec in sub_data]),2),
                         'qty': round(sum([rec.get('qty') for rec in sub_data]),2)})
        return {
            'doc_ids': docids,
            'doc_model': 'inno.purchase',
            'docs': records,
            'data': new_data}
