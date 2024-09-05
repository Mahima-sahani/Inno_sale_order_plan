import datetime
from odoo import models, api


class ReportCargo(models.AbstractModel):
    _name = 'report.inno_packaging.report_print_order_sheet'
    _description = 'Will prepare the data for order sheet'

    @api.model
    def _get_report_values(self, docids, data=None):
        record = self.env['inno.packaging.invoice'].browse(docids)
        invoice_group_data = list()
        for rec in record.pack_invoice_line_ids.mapped('invoice_group'):
            group_data = record.pack_invoice_line_ids.filtered(lambda pil: pil.invoice_group.id == rec.id)
            area_sq_yard = str(round(sum([rec.product_id.product_template_attribute_value_ids.product_attribute_value_id.size_id.area for rec in group_data]), 3))
            split_len = area_sq_yard.split('.')[1].__len__()
            if split_len < 3:
                area_sq_yard = area_sq_yard + '0' * (3 - split_len)
            amount = str(round(sum([rec.amount for rec in group_data]), 2))
            split_len = amount.split('.')[1].__len__()
            if split_len < 2:
                amount = amount + '0' * (2 - split_len)
            rate_sq_ft = str(round(float(amount)/float(area_sq_yard), 2))
            split_len = rate_sq_ft.split('.')[1].__len__()
            if split_len < 2:
                rate_sq_ft = rate_sq_ft + '0' * (2 - split_len)
            invoice_group_data.append({'design': rec.name, 'total_pcs': group_data.__len__(),
                                       'area_sq_feet': area_sq_yard, 'amount': amount,
                                       'rate_sq_ft': rate_sq_ft})
            
        # total_sq_ft = str(round(sum([float(rec.get('area_sq_feet')) for rec in invoice_group_data]), 3))
        total_sq_ft = record.total_area
        split_len = total_sq_ft.split('.')[1].__len__()
        if split_len < 3:
            # total_sq_ft = total_sq_ft + '0' * (3 - split_len)
            total_sq_ft = record.total_area

        total_amount = str(round(sum([float(rec.get('amount')) for rec in invoice_group_data]), 2))
        split_len = total_amount.split('.')[1].__len__()
        if split_len < 2:
            total_amount = total_amount + '0' * (2 - split_len)
        data = {
            'importer': {
                'name': record.partner_id.name, 'street': record.partner_id.street,
                'city': f"{record.partner_id.city}, {record.partner_id.state_id.code}-{record.partner_id.zip}",
                'country': 'USA' if record.partner_id.country_id.code == 'US' else record.partner_id.country_id.code
                },
            'consignee_importer': {
                'name': record.consignee_id.name, 
                'street': record.consignee_id.street,
                'city': f"{record.consignee_id.city}, {record.consignee_id.state_id.code}-{record.consignee_id.zip}",
                'country': 'USA' if record.consignee_id.country_id.code == 'US' else record.consignee_id.country_id.code
                },

            'delivery term': record.delivery_term, 'shipment_mode': record.transportation_type.upper(),
            'discharge_port': record.port_of_discharge, 'description': record.description_of_goods,
            'place_state_code': f"{record.partner_id.city}, {record.partner_id.state_id.code} ({'USA' if record.partner_id.country_id.code == 'US' else record.partner_id.country_id.code})",
            'dec_date': record.date.strftime('%d/%b/%Y'), 'invoice_group_data': invoice_group_data,
            'total_pcs': sum([rec.get('total_pcs') for rec in invoice_group_data]),
            'total_sq_ft': total_sq_ft,
            'total_amount': total_amount,
            'order_no': record.order_sheet_no
                }
        return {
            'doc_ids': docids,
            'doc_model': 'inno.packaging',
            'docs': record,
            'data': data}
