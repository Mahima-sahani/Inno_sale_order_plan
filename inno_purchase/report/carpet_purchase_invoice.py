from datetime import datetime
from odoo import models, api,_
from odoo.exceptions import UserError, ValidationError, MissingError
from num2words import num2words
import logging

_logger = logging.getLogger(__name__)

class ReportPurchaseChallan(models.AbstractModel):
    _name = 'report.inno_purchase.carpet_purchase_invoice'
    _description = 'Carpet Purchase Invoice'

    @api.model
    def _get_report_values(self, docids, data=None):
        records = self.env['account.move'].browse(docids)
        doc_date = records.invoice_date.strftime("%d/%b/%Y") if records.invoice_date else False
        supplier_date = records.supplier_date.strftime("%d/%b/%Y") if records.supplier_date else False
        
        deal_qtys = {}
        total_qty = []
        total_deal_qty = []

        tax_dict = {}
        serial_number = {}
        subtotal = []

        for tax in records.tax_totals.get('groups_by_subtotal')['Untaxed Amount']:
            tax_dict[tax.get('tax_group_name')] = tax.get("tax_group_amount")

        for index,stock_move_line in enumerate(records.invoice_line_ids, start=1):

            total_qty.append(stock_move_line.quantity)
            total_deal_qty.append(float(stock_move_line.inno_area))
            serial_number[stock_move_line.id] = index
            tax_name = stock_move_line.purchase_line_id.taxes_id.name
            subtotal.append(stock_move_line.price_subtotal)

        igst = tax_dict.get('IGST', False)
        sgst = tax_dict.get('SGST', False)
        cgst = tax_dict.get('CGST', False)
        cess = tax_dict.get('CESS', False)

        data = {
                'deal_qty': deal_qtys,
                'total_qty': sum(total_qty),
                'total_deal_qty': sum(total_deal_qty),
                'amount_untaxed': records.tax_totals.get('amount_untaxed'),
                'amount_total': records.tax_totals.get('amount_total'),
                'serial_number': serial_number,
                'amount_in_word': num2words(round(records.tax_totals.get('amount_total'),3)),
                'doc_date': doc_date,
                'supplier_date': supplier_date,
                'tax_name': stock_move_line.purchase_line_id.taxes_id.name,
                'subtotal': sum(subtotal),
                'tex_dict': tax_dict
            }

        if igst:
            data['igst'] = igst
        if sgst:
            data['sgst'] = sgst
        if cgst:
            data['cgst'] = cgst
        if cess:
            data['cess'] = cess

        return {
            'doc_ids': docids,
            'doc_model': 'purchase.order',
            'docs': records,
            'data': data,
        }
