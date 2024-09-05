from odoo import models, api
import base64
from io import BytesIO
import qrcode


class ReportPrintCustomLabel(models.AbstractModel):
    _name = 'report.inno_packaging.report_print_custom_label'
    _description = "Will generate a label for the products"

    @api.model
    def _get_report_values(self, docids, data=None):
        records = self.env['stock.quant.package'].browse(docids)
        data = dict()
        for record in records:
            planning_id = self.env['inno.sale.order.planning'].search([('sale_order_id', '=', record.sale_id.id)])
            if planning_id:
                planning_line = planning_id.sale_order_planning_lines.filtered(lambda pl: pl.product_id.id == record.quant_ids.product_id.id)
                if planning_line:
                    qr = self.generate_qrcode(f"{planning_id.order_no}|{record.quant_ids.product_id.default_code}_{record.id}")
                    data[record.id] = {'buyer_upc_code': planning_line.buyer_up_code, 'qr_code': qr,
                                       'po_number': planning_id.order_no}
            size_rec = record.quant_ids.product_id.product_template_attribute_value_ids.filtered(lambda al: al.attribute_id.name in ['size', 'Size']).product_attribute_value_id
            if size_rec and record.id in data.keys():
                data.get(record.id).update({'size': size_rec[0].name})
            elif size_rec:
                data[record.id] = {'size': size_rec[0].name}
            product_barcodes = record.barcode_ids.filtered(lambda bcode: bcode.state == '8_done')
            if product_barcodes:
                product_barcodes[0].state = '9_packaging'
        return {
            'doc_ids': docids,
            'doc_model': 'stock.quant.package',
            'docs': records,
            'data': data}

    @staticmethod
    def generate_qrcode(qr_data):
        qr = qrcode.QRCode(
            version=6,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=5,
            border=2,
        )
        qr.add_data(qr_data)
        img = qr.make_image()
        temp = BytesIO()
        img.save(temp, format="PNG")
        return base64.b64encode(temp.getvalue())
