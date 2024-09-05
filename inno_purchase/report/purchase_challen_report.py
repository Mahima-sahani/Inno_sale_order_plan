import datetime
from odoo import models, api, _
from odoo.exceptions import UserError, ValidationError, MissingError


class ReportPurchaseChallan(models.AbstractModel):
    _name = 'report.inno_purchase.report_purchase_challan'
    _description = 'Will Provide the report worker wise outstanding reports'


    def get_machine_name(self, rec):
        if rec.receive_line_id.receive_id.types == 'tufting_cloth_weaving':
            return f"Power Loom {rec.machines}"
        elif rec.receive_line_id.receive_id.types == 'third_backing_cloth':
            return f"Cloth Weaving {rec.machines}"
        else:
            return 'no'

    @api.model
    def _get_report_values(self, docids, data=None):
        new_data = {}
        records = self.env['inno.receive'].sudo().browse(docids)
        if records.types in ['tufting_cloth_weaving', 'third_backing_cloth']:
            sub_data = [
                {'product': f"{rec.receive_line_id.product_id.default_code if rec.receive_line_id.product_id.default_code else rec.receive_line_id.product_id.name}",
                 'types': records.types, 'hsn': rec.receive_line_id.product_id.l10n_in_hsn_code or 'N/A',
                 'qty': rec.receive_qty, 'unit': rec.receive_line_id.purchase_line_id.deal_uom_id.name if rec.receive_line_id.receive_id.types in ['tufting_cloth_weaving','third_backing_cloth'] else rec.receive_line_id.uom_id.name,
                 'machine': self.get_machine_name(rec), 'weight_meter': rec.weight_per_mtr,
                 'deal_qty':  rec.invoice_qty,
                 'deal_unit': rec.receive_line_id.deal_uom_id.name,
                 'remark': rec.receive_line_id.remarks, } for rec in records.inno_receive_line.inno_machine_line if rec.receive_line_id.product_id]
        else:
            sub_data = [
                {'product': f"{rec.product_id.default_code if rec.product_id.default_code else rec.product_id.name}",
                 'types': records.types, 'hsn': rec.product_id.l10n_in_hsn_code or 'N/A',
                 'qty': rec.receive_qty,
                 'unit': rec.purchase_line_id.deal_uom_id.name if rec.receive_id.types in ['tufting_cloth_weaving',
                                                                                           'third_backing_cloth'] else rec.uom_id.name,
                  'weight_meter': rec.weight_per_mtr,
                 'deal_qty': rec.invoice_stock_qty if rec.invoice_stock_qty > 0.00 else rec.invoice_qty,
                 'deal_unit': rec.deal_uom_id.name,
                 'remark': rec.remarks, } for rec in records.inno_receive_line if rec.product_id]
        if records:
            new_data.update({'cloth': "no", })
            if records.inno_purchase_id.types == 'yarn':
                new_data.update({'header': "Yarn Purchase Challan", })
            if records.inno_purchase_id.types == 'wool':
                new_data.update({'header': "Wool Purchase Challan", })
            if records.inno_purchase_id.types == 'purchase':
                new_data.update({'header': "Purchase Challan", })
            if records.types == 'tufting_cloth_weaving':
                new_data.update({'header': "TUFTING CLOTH WEAVING CHALLAN", 'cloth': "yes",})
            if records.types == 'newar_production':
                new_data.update({'header': "NEWAR PRODUCTION CHALLAN", })
            if records.types == 'tana_job_order':
                new_data.update({'header': "TANA JOB ORDER CHALLAN", })
            if records.types == 'third_backing_cloth':
                new_data.update({'header': "THIRD BACKING CLOTH CHALLAN", 'cloth': "yes",})

            if records.types == 'spinning':
                new_data.update({'header': "SPINNING JOB WORK CHALLAN", })
            new_data.update({'supplier': records.inno_purchase_id.subcontractor_id.name, 'types': records.types,
                             'code': records.inno_purchase_id.subcontractor_id.name,
                             "address": records.inno_purchase_id.subcontractor_id.street,
                             'mobile': '' if records.inno_purchase_id.subcontractor_id.mobile == 'NULL' else records.inno_purchase_id.subcontractor_id.mobile,
                             'gstin': records.inno_purchase_id.subcontractor_id.vat, 'doc': records.reference,
                             'ref_doc': records.inno_purchase_id.reference,
                             'docDate': records.date.strftime('%d/%m/%Y') if records.date else False,
                             'Received_By': records.received_by.name, 'Godown': records.location.warehouse_id.name,
                             'Supplier Doc': records.receive_docs, 'Supplier Date': records.supplier_date.strftime(
                    '%d/%m/%Y') if records.supplier_date else False,
                             'receipt': records.receipt_no})
        new_data.update({'sub_data': sub_data,
                         'deal_qty': round(sum([rec.get('deal_qty') for rec in sub_data]),2),
                         'qty': round(sum([rec.get('qty') for rec in sub_data]),2)})
        return {
            'doc_ids': docids,
            'doc_model': 'inno.purchase',
            'docs': records,
            'data': new_data}
