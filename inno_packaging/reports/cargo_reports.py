import datetime
from odoo import models, api


class ReportCargo(models.AbstractModel):
    _name = 'report.inno_packaging.report_print_cargo_reports'
    _description = 'Will prepare the data for displaying the template.'


    def company_details(self):
        pass

    @api.model
    def _get_report_values(self, docids, data=None):
        record = self.env['inno.packaging.invoice'].browse(docids)
        gross_weight = str(record.gross_weight)
        split_len = gross_weight.split('.')[1].__len__()
        if split_len < 3:
            gross_weight = gross_weight + '0' * (3 - split_len)
        data = {
            'consignee': {
                'name': record.partner_id.name, 'street': record.partner_id.street,
                'city': f"{record.partner_id.city}, {record.partner_id.state_id.code}-{record.partner_id.zip}",
                'country': 'USA' if record.partner_id.country_id.code == 'US' else record.partner_id.country_id.code},
            'place_of_receipt': record.place_of_receipt, 'loading_port': record.port_of_loading,
            'discharge_port': record.port_of_discharge, 'description': record.description_of_goods,
            'roll_no': len(set(record.pack_invoice_line_ids.mapped('roll_no'))),
            'gross_weight': gross_weight,
            'place_state_code': f"{record.partner_id.city}, {record.partner_id.state_id.code} ({'USA' if record.partner_id.country_id.code == 'US' else record.partner_id.country_id.code})",
            'dec_date': record.date.strftime('%d/%b/%Y'),
                }
        return {
            'doc_ids': docids,
            'doc_model': 'inno.packaging',
            'docs': record,
            'data': data}