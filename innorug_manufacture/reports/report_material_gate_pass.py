import datetime
import qrcode, base64
from io import BytesIO
from odoo import models, api


class ReportMaterialGatePass(models.AbstractModel):
    _name = 'report.innorug_manufacture.report_material_gate_pass'
    _description = 'Will prepare the data for displaying the template.'

    @api.model
    def _get_report_values(self, docids, data=None):
        record = self.env['stock.picking'].browse(docids)
        pick_type = data.get('type')
        qr_code = self.generate_qrcode(record)
        material = dict()
        for rec in record.move_ids:
            shade = rec.product_id.product_template_attribute_value_ids.filtered(
                lambda al: al.attribute_id.name in ['shade', 'Shade', 'SHADE'])
            material[rec.product_id.id] = {
                'product_name': rec.product_id.name,
                'shade': shade[0].name if shade else 'N/A',
                'qty': round(rec.quantity_done, 3),
                'uom': rec.product_uom.name
            }
        data = {'company': {'company_name': record.company_id.name, 'logo': record.company_id.logo,
                            'address_line1': f"{record.company_id.street}, {record.company_id.street}-"
                                             f"{record.company_id.zip}",
                            'address_line2': f"{record.company_id.city}, ({record.company_id.state_id.code}),"
                                             f"{record.company_id.country_id.name}",
                            'mobile': record.company_id.mobile, 'gstin': record.company_id.vat,
                            'state_code': record.company_id.state_id.code
                            },
                'received_by': record.partner_id.name, 'issue_by': self.env.user.name,
                'date': datetime.datetime.today().strftime('%d/%m/%Y'), 'gate_pass': record.name, 'qrcode': qr_code,
                'site': '-', 'division': 'N/A', 'materials': material.values(), 'document': record.origin,
                'total_material': sum([rec.qty_done for rec in record.move_line_ids]),
                'picking_type': pick_type,
                'source_location': record.location_id.warehouse_id.name if pick_type == 'internal' else False,
                'dest_location': record.location_dest_id.warehouse_id.name if pick_type == 'internal' else False}
        return {
            'doc_ids': docids,
            'doc_model': 'stock.picking',
            'docs': record,
            'data': data}

    def generate_qrcode(self, record):
        qr = qrcode.QRCode(
            version=6,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=5,
            border=2,
        )
        qr_data = (f'"received_by": "{record.partner_id.name}", "issue_by": "{self.env.user.name}",'
                   f' "date": "{datetime.datetime.today().date()}", "gate_pass": "{record.name}", "id": {record.id},'
                   f' "model": "stock.picking"')
        qr.add_data(qr_data)
        img = qr.make_image()
        temp = BytesIO()
        img.save(temp, format="PNG")
        return base64.b64encode(temp.getvalue())

