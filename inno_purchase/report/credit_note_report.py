import datetime
from odoo import models, api,_
from odoo.exceptions import UserError, ValidationError, MissingError


class ReportPurchaseCreditNote(models.AbstractModel):
    _name = 'report.inno_purchase.report_purchase_credit_note'
    _description = 'Will Provide the report worker wise outstanding reports'


    @api.model
    def _get_report_values(self, docids, data=None):
        new_data = {}
        tax_data = {}
        records = self.env['inno.receive'].sudo().browse(docids)
        bill_id = self.env['account.move'].sudo().search(
            [('receive_id', '=', records.id), ('move_type', '=', 'in_refund')])
        sub_data = [
            {'product': rec.product_id.default_code if rec.product_id else rec.name,
             'hsn': rec.product_id.l10n_in_hsn_code or 'N/A', 'indent': '',
             'reason': rec.name,
             'rate': rec.price_unit, 'amont': rec.price_subtotal,
             'gst': ', '.join(rec.tax_ids.mapped('name')), } for rec in bill_id.invoice_line_ids if rec.price_unit >0.00]
        payble = float(bill_id.tax_totals.get('amount_total_rounded') if bill_id.tax_totals.get(
            'formatted_amount_total_rounded') else records.tax_totals.get(
            'amount_total'))
        tax_data.update(
            {'untax_amout': round(bill_id.tax_totals.get('amount_untaxed'), 2),
             'amount_in_words': bill_id.currency_id.amount_to_text(payble),
             'gross_amount': bill_id.tax_totals.get('formatted_amount_total_rounded') if bill_id.tax_totals.get(
                 'formatted_amount_total_rounded') else bill_id.tax_totals.get('formatted_amount_total'),
             'DESC': ', '.join(
                 bill_id.invoice_line_ids.tax_ids.mapped('name')) if bill_id.invoice_line_ids.tax_ids else 'GST 0%',
             'rounding_amount': bill_id.tax_totals.get('rounding_amount'),
             'Taxable': round(bill_id.tax_totals.get('amount_untaxed'), 2)})

        invoice_gst = {}
        if bill_id.tax_totals.get('groups_by_subtotal').get('Untaxed Amount'):
            tax_data.update({'tax': 'yes'})
            for rec in bill_id.tax_totals.get('groups_by_subtotal').get('Untaxed Amount'):
                invoice_gst.update({rec.get('tax_group_name'): round(rec.get('tax_group_amount'), 2)})
        else:
            tax_data.update({'tax': 'no'})

        if records:
            if records.inno_purchase_id.types == 'yarn':
                new_data.update({'header': "DEBIT NOTE (Outward)", })
            if records.inno_purchase_id.types == 'wool':
                new_data.update({'header': "DEBIT NOTE (Outward)", })
            if records.inno_purchase_id.types == 'purchase':
                new_data.update({'header': "DEBIT NOTE (Outward)", })
            new_data.update({'supplier': records.inno_purchase_id.subcontractor_id.name, 'types': records.types,
                             'code': records.inno_purchase_id.subcontractor_id.name,
                             "address": records.inno_purchase_id.subcontractor_id.street,
                             'mobile': '' if records.inno_purchase_id.subcontractor_id.mobile == 'NULL' else records.inno_purchase_id.subcontractor_id.mobile,
                             'gstin': records.inno_purchase_id.subcontractor_id.vat,
                             'Supplier Doc Date': records.invoice_date.strftime(
                                 '%d/%m/%Y') if records.invoice_date else False, 'doc': bill_id.name,
                             'challan': records.reference,
                             'ref_doc': records.inno_purchase_id.reference, 'docDate': records.date, 'ref': bill_id.ref,
                             'Received_By': self.env.user.name, 'Godown': records.location.warehouse_id.name,
                             'Supplier Doc': records.receive_invoice,
                             'Supplier Date': records.date.strftime('%d/%m/%Y') if records.date else False,
                             'receipt': records.receipt_no})
        new_data.update({'sub_data': sub_data, 'tax_data': tax_data, 'invoice_gst': invoice_gst,
                         'deal_qty': 0.0,
                         'total_amount': sum([rec.get('amont') for rec in sub_data]),
                         'qty': 0.0})
        return {
            'doc_ids': docids,
            'doc_model': 'inno.purchase',
            'docs': records,
            'data': new_data}