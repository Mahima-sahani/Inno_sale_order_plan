from odoo import models, api
from barcode import Code128, UPCA
from barcode.writer import ImageWriter
import base64
from io import BytesIO
import qrcode
import random, string
from reportlab.graphics import barcode


class ReportPrintFullLabel(models.AbstractModel):
    _name = 'report.inno_packaging.report_print_upc_label'
    _description = "Will generate a label for the products"

    @api.model
    def _get_report_values(self, docids, data=None):
        docids = data.get('package')
        random_code = ''.join(random.SystemRandom().choice(string.ascii_uppercase) for _ in range(5))
        records = self.env['stock.quant.package'].browse(int(data.get('package')))
        sale =int(data.get('sale', 0))
        barcode_no = data.get('barcode')
        group_no = data.get('group')
        data = dict()
        barcode.createBarcodeDrawing('UPCA', )
        for record in records:
            planning_id = self.env['inno.sale.order.planning'].search([('sale_order_id', '=', sale)])
            if planning_id:
                planning_line = planning_id.sale_order_planning_lines.filtered(lambda pl: pl.product_id.id == record.quant_ids.product_id.id)
                if planning_line:
                    if record.quant_ids.product_id.buyer_upc_code:
                        barcodea = base64.b64encode(barcode.createBarcodeDrawing('UPCA', value=record.quant_ids.product_id.buyer_upc_code, height=300, width=300).asString('png'))
                    else:
                        barcodea = False
                    qr = self.generate_qrcode(f"{planning_id.order_no}|{record.quant_ids.product_id.default_code}_{random_code}")
                    data[record.id] = {'buyer_upc_code': record.quant_ids.product_id.buyer_upc_code, 'barcode': barcodea,
                                       'qr_code': qr, 'po_number': planning_id.order_no, 'random_code': random_code}
            size_rec = record.quant_ids.product_id.product_template_attribute_value_ids.filtered(lambda al: al.attribute_id.name in ['size', 'Size']).product_attribute_value_id
            if size_rec:
                actual_size = size_rec[0].size_id
                size_str = (f"{str(actual_size.length) + 'ft' if actual_size.length > 0.0 else ''}" +
                            f" {str(actual_size.len_fraction) + 'in' if actual_size.len_fraction > 0.0 else ''}" +
                            f"{' x ' if actual_size.length > 0.0 or actual_size.len_fraction > 0.0 else ''}" +
                            f"{str(actual_size.width) + 'ft' if actual_size.width > 0.0 else ''}" +
                            f" {str(actual_size.width_fraction) + 'in' if actual_size.width_fraction > 0.0 else ''}")
                if actual_size and record.id in data.keys():
                    data.get(record.id).update({'size': size_str})
                elif actual_size:
                    data[record.id] = {'size': size_str}
            data.get(record.id).update({'package_barcode': base64.b64encode(barcode.createBarcodeDrawing('Code128', value=f"Group No #{group_no}", height=400, width=600).asString('png'))})
            data.get(record.id).update({'package_barcode_data': f"Group No #{group_no}"})
            data.get(record.id).update({'product_barcode': self.get_barcode(str(barcode_no))})
        return {
            'doc_ids': docids,
            'doc_model': 'stock.quant.package',
            'docs': records,
            'data': data}

    @staticmethod
    def get_barcode(data, upca=False):
        svg_img_bytes = BytesIO()
        if upca:
            UPCA(data, writer=ImageWriter()).write(svg_img_bytes)
        else:
            Code128(data, writer=ImageWriter()).write(svg_img_bytes)
        return base64.b64encode(svg_img_bytes.getvalue())

    def validate_create_barcode(self, upc):
        code = upc
        checksum = upc[-1]

        if len(upc) < self._digits:
            checksum = self.validate_checksum()
            if checksum:
                self.code += checksum
            else:
                raise ValueError(f'Invalid upc {code}!')
        else:
            valid = self.validate_checksum()
            if not valid:
                raise ValueError(f'Invalid upc {code}, validate checksum failed!')
        return super().validate_create_barcode(self.filename, size=2)

    @staticmethod
    def generate_qrcode(qr_data):
        qr = qrcode.QRCode(
            version=3,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=5,
            border=2,
        )
        qr.add_data(qr_data)
        img = qr.make_image()
        temp = BytesIO()
        img.save(temp, format="PNG")
        return base64.b64encode(temp.getvalue())
