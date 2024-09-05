from datetime import datetime
from odoo import models, api,_
from odoo.exceptions import UserError, ValidationError, MissingError
from num2words import num2words
import logging

_logger = logging.getLogger(__name__)

class ReportPurchaseChallan(models.AbstractModel):
    _name = 'report.inno_purchase.carpet_purchase_order'
    _description = 'Carpet Purchase Order'

    @api.model
    def _get_report_values(self, docids, data=None):
        records = self.env['purchase.order'].browse(docids)
        formatted_date_planned = records.date_planned.strftime("%d/%b/%Y")
        formatted_order_date = records.date_order.strftime("%d/%b/%Y")
        
        deal_qtys = {}
        total_qty = []
        total_deal_qty = []

        tax_dict = {}
        serial_number = {}
        subtotal = []

        for tax in records.tax_totals.get('groups_by_subtotal')['Untaxed Amount']:
            tax_dict[tax.get('tax_group_name')] = tax.get("tax_group_amount")

        for index,purchase_order_line in enumerate(records.order_line, start=1):
            product_variant = purchase_order_line.product_id.product_template_variant_value_ids.name
            # size = self.env['inno.size'].search([('name','=',product_variant)])
            # area = size.area
            deal_qty = (sum([float(rec.total_area) for rec in purchase_order_line]))
            deal_qtys[purchase_order_line.id] = deal_qty
            total_qty.append(purchase_order_line.product_qty)
            total_deal_qty.append(deal_qty)
            serial_number[purchase_order_line.id] = index
            tax_name = purchase_order_line.taxes_id.name
            subtotal.append(purchase_order_line.price_subtotal)
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
                'date_planned': formatted_date_planned,
                'date_order': formatted_order_date,
                'tax_name': purchase_order_line.taxes_id.name,
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
