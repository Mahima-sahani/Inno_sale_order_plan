import datetime
from odoo import models, api, _
from odoo.exceptions import UserError, ValidationError, MissingError


class ReportPurchaseOrder(models.AbstractModel):
    _name = 'report.inno_purchase.report_material_purchase_order'
    _description = 'Will Provide the report worker wise outstanding reports'

    @api.model
    def _get_report_values(self, docids, data=None):
        new_data = {}
        tax_data = {}
        records = self.env['inno.purchase'].sudo().browse(docids)
        sub_data = [
            {'product': rec.product_id.default_code, 'hsn': rec.product_id.l10n_in_hsn_code or 'N/A', 'indent': '',
             'qty': rec.deal_qty if rec.inno_purchase_id.types in ['tufting_cloth_weaving',
                                                                   'third_backing_cloth'] else rec.product_qty,
             'unit': rec.deal_uom_id.name if rec.inno_purchase_id.types in ['tufting_cloth_weaving',
                                                                            'third_backing_cloth'] else rec.uom_id.name,
             'deal_qty': rec.deal_qty,
             'deal_unit': rec.deal_uom_id.name, 'discount': rec.discount,
             'rate': rec.rate, 'amont': rec.price_subtotal, 'remark': rec.remarks, 'types': records.types,
             'gst': ', '.join(rec.tax_id.mapped('name')), } for rec in records.inno_purchase_line]
        tax_data.update(
            {'untax_amout': records.tax_totals.get('amount_untaxed'), 'amount_in_words': records.amount_total_words,
             'gross_amount': records.tax_totals.get('formatted_amount_total'), 'DESC': ', '.join(
                records.inno_purchase_line.tax_id.mapped('name')) if records.inno_purchase_line.tax_id else 'GST 0%',
             'Taxable': records.tax_totals.get('amount_untaxed')})
        invoice_gst = {}
        if records.tax_totals.get('groups_by_subtotal').get('Untaxed Amount'):
            tax_data.update({'tax': 'yes'})
            for rec in records.tax_totals.get('groups_by_subtotal').get('Untaxed Amount'):
                invoice_gst.update({rec.get('tax_group_name'): round(rec.get('tax_group_amount'), 3)})
        else:
            tax_data.update({'tax': 'no'})

        if records:
            if records.types == 'yarn':
                new_data.update({'header': "Yarn Purchase Order", })
            if records.types == 'wool':
                new_data.update({'header': "Wool Purchase Order", })
            if records.types == 'purchase':
                new_data.update({'header': "Purchase Order", })
            if records.types == 'tufting_cloth_weaving':
                new_data.update({'header': "TUFTING CLOTH WEAVING", })
            if records.types == 'newar_production':
                new_data.update({'header': "NEWAR PRODUCTION", })
            if records.types == 'tana_job_order':
                new_data.update({'header': "TANA JOB ORDER", })
            if records.types == 'third_backing_cloth':
                new_data.update({'header': "THIRD BACKING CLOTH", })
            if records.types == 'spinning':
                new_data.update({'header': "SPINNING JOB WORK", })
            new_data.update({'supplier': records.subcontractor_id.name, 'code': records.subcontractor_id.name,
                             'types': records.types, "address": records.subcontractor_id.street,
                             'mobile': '' if records.subcontractor_id.mobile == 'NULL' else records.subcontractor_id.mobile,
                             'gstin': records.subcontractor_id.vat, 'doc': records.reference,
                             'docDate': records.issue_date.strftime('%d/%m/%Y') if records.issue_date else False,
                             'docDue': records.expected_received_date.strftime(
                                 '%d/%m/%Y') if records.expected_received_date else False,
                             'reverse_charge': 'No'})
        new_data.update({'sub_data': sub_data, 'tax_data': tax_data, 'invoice_gst': invoice_gst,
                         'deal_qty': sum([rec.get('deal_qty') for rec in sub_data]),
                         'total_amount': round(sum([rec.get('amont') for rec in sub_data]),3),
                         'qty': sum([rec.get('qty') for rec in sub_data])})
        return {
            'doc_ids': docids,
            'doc_model': 'inno.purchase',
            'docs': records,
            'data': new_data}
