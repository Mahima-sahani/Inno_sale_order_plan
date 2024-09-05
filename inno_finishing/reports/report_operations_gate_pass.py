import datetime
import qrcode, base64
from io import BytesIO
from odoo import models, api


class ReportCarpetGatePass(models.AbstractModel):
    _name = 'report.inno_finishing.report_operation_gate_pass'
    _description = 'Will prepare the data for displaying the template.'

    @api.model
    def _get_report_values(self, docids, data=None):
        record = self.env['finishing.work.order'].browse(docids)
        qr_code = self.generate_qrcode(record)
        prs =record.jobwork_barcode_lines.mapped('product_id')
        products = [{
            'product': transfer_line.default_code, 'qty' : len(record.jobwork_barcode_lines.filtered(lambda code : code.product_id.id in transfer_line.ids))
        } for transfer_line in prs]

        data = {'company': {'company_name': record.company_id.name, 'logo': record.company_id.logo,
                            'address_line1': f"{record.company_id.street}, {record.company_id.street}-"
                                             f"{record.company_id.zip}",
                            'address_line2': f"{record.company_id.city}, ({record.company_id.state_id.code}),"
                                             f"{record.company_id.country_id.name}",
                            'mobile': record.company_id.mobile, 'gstin': record.company_id.vat,
                            'state_code': record.company_id.state_id.code
                            },
                'received_by': record.subcontractor_id.name,
                'issue_by': self.env.user.name,
                'date': datetime.datetime.today().date(),
                'gate_pass': record.name,
                'qrcode': qr_code,
                'site': '-',
                'division': 'MAIN',
                'products': {
            'data' : products
        }
                }
        return {
            'doc_ids': docids,
            'doc_model': 'finishing.work.order',
            'docs': record,
            'data': data}

    def generate_qrcode(self, record):
        qr = qrcode.QRCode(
            version=6,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=5,
            border=2,
        )
        qr_data = (f'"received_by": "{record.subcontractor_id.name}", "issue_by": "{self.env.user.name}",'
                   f' "date": "{datetime.datetime.today().date()}", "gate_pass": "{record.name}", "id": {record.id},'
                   f' "model": "finishing.work.order')
        qr.add_data(qr_data)
        img = qr.make_image()
        temp = BytesIO()
        img.save(temp, format="PNG")
        return base64.b64encode(temp.getvalue())