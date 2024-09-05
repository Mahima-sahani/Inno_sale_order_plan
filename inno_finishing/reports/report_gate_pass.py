import datetime
import qrcode, base64
from io import BytesIO
from odoo import models, api


class ReportMaterialGatePass(models.AbstractModel):
    _name = 'report.inno_finishing.report_material_gate_pass'
    _description = 'Will prepare the data for displaying the template.'

    @api.model
    def _get_report_values(self, docids, data=None):
        record = self.env['inno.carpet.transfer'].browse(docids)
        qr_code = self.generate_qrcode(record)
        prs =record.barcode_line
        # products = [{
        #     'product': transfer_line.default_code,
        #     'qty': len(record.barcode_line.filtered(lambda code : code.product_id.id in transfer_line.ids))
        # } for transfer_line in prs]
        products = []
        # for transfer_line in prs:
        #     qty = len(record.barcode_line.filtered(lambda code : code.product_id.id in transfer_line.ids))
        #     products.append({'product': transfer_line.default_code, 'qty': qty,
        #                      'area': transfer_line.inno_finishing_size_id.area_sq_yard * qty})
        # size = [{
        #     'size': jobwork.name,
        #     'qty': len(record.barcode_line.filtered(lambda pv: pv.product_id.inno_finishing_size_id == jobwork)),
        # } for jobwork in record.barcode_line.product_id.inno_finishing_size_id]

        products = [{'size': size.name, 'qty': len(prs.filtered(lambda prd: prd.product_id.product_template_attribute_value_ids.product_attribute_value_id.size_id.id == size.id))} for size in prs.product_id.product_template_attribute_value_ids.product_attribute_value_id.size_id]
        data = {'company': {'company_name': record.company_id.name, 'logo': record.company_id.logo,
                            'address_line1': f"{record.company_id.street}, {record.company_id.street}-"
                                             f"{record.company_id.zip}",
                            'address_line2': f"{record.company_id.city}, ({record.company_id.state_id.code}),"
                                             f"{record.company_id.country_id.name}",
                            'mobile': record.company_id.mobile, 'gstin': record.company_id.vat,
                            'state_code': record.company_id.state_id.code
                            },
                'received_by': record.person_id.name,
                'issue_by': self.env.user.name,
                'date': datetime.datetime.today().date(),
                'source': record.source_location_id.warehouse_id.name,
                'destination': record.dest_location_id.warehouse_id.name,
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
            'doc_model': 'inno.carpet.transfer',
            'docs': record,
            'data': data}

    def generate_qrcode(self, record):
        qr = qrcode.QRCode(
            version=6,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=5,
            border=2,
        )
        qr_data = (f'"received_by": "{record.person_id.name}", "issue_by": "{self.env.user.name}",'
                   f' "date": "{datetime.datetime.today().date()}", "gate_pass": "{record.name}", "id": {record.id},'
                   f' "model": "inno.carpet.transfer')
        qr.add_data(qr_data)
        img = qr.make_image()
        temp = BytesIO()
        img.save(temp, format="PNG")
        return base64.b64encode(temp.getvalue())