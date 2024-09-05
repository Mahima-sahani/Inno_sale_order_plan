from odoo import models, fields, api, _
from odoo.exceptions import UserError
from io import BytesIO, StringIO
import xlsxwriter
import base64
from num2words import num2words
from pypdf import PdfReader,PdfWriter

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from io import BytesIO
from reportlab.lib.colors import black

class PackagingInvoice(models.Model):
    _name = 'inno.packaging.invoice'
    _description = 'Packaging Invoice'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Invoice No.', default='/')
    date = fields.Date(string='Invoice Date', default=fields.Date.today)
    partner_id = fields.Many2one(comodel_name='res.partner', string="Buyer's Name")
    exchange_rate = fields.Float(digits=(10, 3), string='Exchange Rate')
    state = fields.Selection(selection=[('draft', 'Draft'), ('container', 'Add Packages'), ('final', "Final Container"), ('done', 'Invoiced')],
                             default='draft')
    pack_invoice_line_ids = fields.One2many(comodel_name='inno.packaging.invoice.line', inverse_name='packing_id')
    packaging_list = fields.Many2one(comodel_name='inno.packaging', string='Packaging List',
                                     domain=[('status', '=', 'invoicing')])
    bale_count = fields.Integer()
    other_reference = fields.Char(string='Other Reference')
    buyer_order_no = fields.Char(string="Buyer's order no")
    buyer_order_date = fields.Date(string="Buyer's order Date")
    pre_carriage_by = fields.Char(string='Pre-Carriage By')
    place_of_receipt = fields.Char(string='Place of Receipt')
    transportation_type = fields.Selection(selection=[('sea', 'BY SEA'), ('air', 'BY AIR'), ('truck', 'BY TRUCK'),
                                                      ('courier', 'COURIER')], string='Ship Method')
    port_of_loading = fields.Char(string='Port of Loading')
    port_of_discharge = fields.Char(string='Port of Discharge')
    description_of_goods = fields.Text(string='Goods Description')
    net_weight = fields.Float(digits=(10, 4), string='Net Weight')
    gross_weight = fields.Float(digits=(10, 4), string='Gross Weight')
    order_sheet_no = fields.Char(string="Order Sheet No")
    delivery_term = fields.Char(string='Delivery Term')
    total_area = fields.Char("")
    consignee_id = fields.Many2one(comodel_name='res.partner', string="Consignee's Name")

    def button_confirm(self):
        self.write({'state': 'container'})

    @api.onchange('packaging_list')
    def onchange_packaging_list(self):
        if not self.packaging_list:
            return
        if self.packaging_list.status != 'invoicing':
            raise UserError(_("This Packaging list is already Packed"))
        vals = []
        for rec in self.packaging_list.stock_quant_lines:
            vals.append((0, 0, {'product_id': rec.product_id.id, 'bale_no': self.bale_count+1,
                                'invoice_group': rec.invoice_group_id.id, 'qty': rec.quantity,
                                'deal_qty': rec.deal_qty, 'rate': rec.invoice_group_id.rate,
                                'roll_no': rec.roll_no, 'net_weight': rec.net_weight,
                                'gross_weight': rec.gross_weight, 'sale_order_id': rec.inno_sale_id.id,
                                'related_so': str(rec.inno_sale_id.id)}))
            self.bale_count += 1
        if vals:
            self.write({'pack_invoice_line_ids': vals})
            self.packaging_list.status = 'done'



    def create_footer_pdf(self,footer_text):
        buffer = BytesIO()

        c = canvas.Canvas(buffer, pagesize=letter)
        width, height = letter

        # Define footer dimensions
        footer_height = 28
        footer_margin = 52.5
        bottom_margin = 5

        # Define total footer width (excluding margins) and signature box width
        total_columns = 12
        total_footer_width = 524
        signature_columns = 4  # Signature box spans 4 columns

        # Calculate the width of one column
        column_width = total_footer_width / total_columns

        # Calculate the width of the signature box
        signature_box_width = signature_columns * column_width

        # Footer text
        footer_text = "Signature & Date"

        # Draw footer box
        c.setStrokeColor(black)
        c.setLineWidth(1)
        c.rect(width - footer_margin - total_footer_width, bottom_margin, total_footer_width, footer_height, stroke=1, fill=0)
        # c.rect(width - footer_margin - total_footer_width, bottom_margin, total_footer_width, footer_height, stroke=1, fill=0)

        # Position of signature box
        signature_box_x = width - footer_margin - signature_box_width
        c.rect(signature_box_x, bottom_margin, signature_box_width, footer_height, stroke=1, fill=0)

        # Draw footer text aligned to the right
        c.setFont("Helvetica", 7)
        text_width = c.stringWidth(footer_text, "Helvetica", 7)
        text_x = signature_box_x + signature_box_width - text_width - 118  # Adjusted to add a little padding from the right
        text_y = (footer_height + 22) / 2  # Adjusted to align vertically within the footer
        c.drawString(text_x, text_y, footer_text)

        # Save the PDF
        c.save()

        buffer.seek(0)
        return buffer

    def add_footer_to_pdf(self,input_pdf_binary, footer_text):
        # Create a footer PDF
        footer_buffer = self.create_footer_pdf(footer_text)
        
        # Read the input PDF from binary
        input_pdf_buffer = BytesIO(input_pdf_binary)
        pdf_reader = PdfReader(input_pdf_buffer)
        footer_pdf_reader = PdfReader(footer_buffer)
        
        pdf_writer = PdfWriter()
        num_pages = len(pdf_reader.pages)
        
        for i in range(num_pages):
            page = pdf_reader.pages[i]
            if i < num_pages - 1:  # Skip adding footer to the last page
                footer_page = footer_pdf_reader.pages[0]
                page.merge_page(footer_page)
            pdf_writer.add_page(page)
        
        # Write the output PDF to a binary buffer
        output_buffer = BytesIO()
        pdf_writer.write(output_buffer)
        output_buffer.seek(0)
        
        # Encode the PDF to Base64
        pdf_base64 = base64.b64encode(output_buffer.read()).decode('utf-8')
        
        return pdf_base64

    def confirm_container(self):
        export_invoice = self.env.ref('inno_packaging.action_inno_export_invoice_reports',
                           raise_if_not_found=False).sudo()._render_qweb_pdf(
            'inno_packaging.action_inno_export_invoice_reports',res_ids=self.id)[0]
        export_invoice = base64.b64encode(export_invoice).decode()
        export_invoice = self.env['ir.attachment'].create({'name': f"Export Invoice {self.name}",
                                                       'type': 'binary', 'datas': export_invoice, 'res_model': 'main.jobwork',
                                                       'res_id': self.id,
                                                       })
        cargo = self.env.ref('inno_packaging.action_report_print_cargo_reports',
                             raise_if_not_found=False).sudo()._render_qweb_pdf(
            'inno_packaging.action_report_print_cargo_reports', res_ids=self.id)[0]
        cargo = base64.b64encode(cargo).decode()
        cargo = self.env['ir.attachment'].create({'name': f"cargo {self.name}",
                                                  'type': 'binary', 'datas': cargo,
                                                  'res_model': 'main.jobwork',
                                                  'res_id': self.id,
                                                  })
        
        packaging_list = self.env.ref('inno_packaging.action_report_print_packaging_list',
                             raise_if_not_found=False).sudo()._render_qweb_pdf(
            'inno_packaging.action_report_print_packaging_list', res_ids=self.id, data={'report_type': 'normal',
                                                                                        'doc_ids': self.id})[0]

        footer_text = 'Your Footer Text Here'
        pdf_base64 = self.add_footer_to_pdf(packaging_list, footer_text)
        
        packaging_list = self.env['ir.attachment'].create({'name': f"packaging list {self.name}",
                                                  'type': 'binary', 'datas': pdf_base64,
                                                  'res_model': 'main.jobwork',
                                                  'res_id': self.id,
                                                  })
        
        order_sheet = self.env.ref('inno_packaging.action_report_print_order_sheet',
                                      raise_if_not_found=False).sudo()._render_qweb_pdf(
            'inno_packaging.action_report_print_order_sheet', res_ids=self.id)[0]
        order_sheet = base64.b64encode(order_sheet).decode()
        order_sheet = self.env['ir.attachment'].create({'name': f"Order Sheet {self.name}",
                                                  'type': 'binary', 'datas': order_sheet,
                                                  'res_model': 'main.jobwork',
                                                  'res_id': self.id,
                                                  })
        group_label = self.env.ref('inno_packaging.action_report_group_label',
                                   raise_if_not_found=False).sudo()._render_qweb_pdf(
            'inno_packaging.action_report_group_label', res_ids=self.id)[0]
        group_label = base64.b64encode(group_label).decode()
        group_label = self.env['ir.attachment'].create({'name': f"Group Label {self.name}",
                                                        'type': 'binary', 'datas': group_label,
                                                        'res_model': 'main.jobwork',
                                                        'res_id': self.id,
                                                        })
        self.message_post(body="Invoice Reports", attachment_ids=[export_invoice.id, cargo.id,
                                                                  packaging_list.id, order_sheet.id, group_label.id])
        self.state = 'final'

    def finalise_container(self):
        self.generate_master_key()
        self.generate_export_invoice_xls()
        for rec in self.pack_invoice_line_ids.sale_order_id:
            picking = rec.picking_ids.filtered(lambda pick: pick.state not in ['done', 'cancel'])
            picking.with_context(skip_backorder=True).button_validate()
        self.state = 'done'

    def generate_mda_package_list(self):
        packaging_list_mda = self.env.ref('inno_packaging.action_report_print_packaging_list',
                                   raise_if_not_found=False).sudo()._render_qweb_pdf(
            'inno_packaging.action_report_print_packaging_list', res_ids=self.id,  data={'doc_ids': self.id})[0]
        packaging_list_mda = base64.b64encode(packaging_list_mda).decode()
        packaging_list_mda = self.env['ir.attachment'].create({'name': f"Packaging List (MDA) {self.name}",
                                                        'type': 'binary', 'datas': packaging_list_mda,
                                                        'res_model': 'main.jobwork',
                                                        'res_id': self.id,
                                                        })
        self.message_post(body="Packaging List (MDA)", attachment_ids=[packaging_list_mda.id])

    def generate_group_label_mda(self):
        group_label_mda = self.env.ref('inno_packaging.action_report_group_label',
                                          raise_if_not_found=False).sudo()._render_qweb_pdf(
            'inno_packaging.action_report_group_label', res_ids=self.id, data={'report_type': 'normal',
                                                                               'doc_ids': self.id})[0]
        group_label_mda = base64.b64encode(group_label_mda).decode()
        group_label_mda = self.env['ir.attachment'].create({'name': f"Group Label (MDA) {self.name}",
                                                               'type': 'binary', 'datas': group_label_mda,
                                                               'res_model': 'main.jobwork',
                                                               'res_id': self.id,
                                                               })
        self.message_post(body="Group Label (MDA)", attachment_ids=[group_label_mda.id])

    def button_invoice(self):
        if self._context.get('report_type') == 'export_invoice':
            report = self.env.ref('inno_packaging.action_inno_export_invoice_reports',
                                  raise_if_not_found=False).report_action(docids=self.id)
        elif self._context.get('report_type') == 'cargo':
            report = self.env.ref('inno_packaging.action_report_print_cargo_reports',
                                  raise_if_not_found=False).report_action(docids=self.id)
        elif self._context.get('report_type') == 'packaging_list':
            report = self.env.ref('inno_packaging.action_report_print_packaging_list',
                                  raise_if_not_found=False).report_action(docids=self.id, data={'report_type': 'normal',
                                                                                                'doc_ids': self.id})
        elif self._context.get('report_type') == 'packaging_list_mda':
            report = self.env.ref('inno_packaging.action_report_print_packaging_list',
                                  raise_if_not_found=False).report_action(docids=self.id, data={'doc_ids': self.id})
        elif self._context.get('report_type') == 'master_key':
            return self.generate_master_key()
        elif self._context.get('report_type') == 'order_sheet':
            report = self.env.ref('inno_packaging.action_report_print_order_sheet',
                                  raise_if_not_found=False).report_action(docids=self.id)
        elif self._context.get('report_type') == 'export_invoice_xls':
            return self.generate_export_invoice_xls()
        elif self._context.get('report_type') == 'group_label':
            report = self.env.ref('inno_packaging.action_report_group_label',
                                  raise_if_not_found=False).report_action(docids=self.id, data={'report_type': 'normal',
                                                                                                'doc_ids': self.id})
        elif self._context.get('report_type') == 'group_label_mda':
            report = self.env.ref('inno_packaging.action_report_group_label',
                                  raise_if_not_found=False).report_action(docids=self.id, data={'doc_ids': self.id})
        else:
            return False
        return report

    def generate_export_invoice_xls(self):
        file_data = BytesIO()
        workbook = xlsxwriter.Workbook(file_data, {})
        sheet = workbook.add_worksheet("Master Key")
        heading = workbook.add_format({"bold": True, "font_size": 10, 'left': True, 'right': True, 'top': True,
                                       'bottom': True, 'valign': 'center'})
        heading2 = workbook.add_format({"bold": True, "font_size": 8, 'left': True, 'right': True, 'top': True,
                                       'bottom': True, 'valign': 'center', 'align': 'vcenter'})
        zero2 = workbook.add_format(
            {'num_format': '#,##0.00', 'right': True, "font_size": 8})
        zero3 = workbook.add_format(
            {'num_format': '#,##0.000', 'right': True, "font_size": 8})
        zero5 = workbook.add_format(
            {'num_format': '#,##0.00000', 'right': True, "font_size": 8})
        bold_border_zero2 = workbook.add_format(
            {'num_format': '#,##0.00', 'left': True, 'right': True, 'top': True, 'bottom': True, "font_size": 8, "bold": True})
        bold_border_zero3 = workbook.add_format(
            {'num_format': '#,##0.000', 'left': True, 'right': True, 'top': True, 'bottom': True, "font_size": 8, "bold": True,})
        wrap_data = workbook.add_format({"font_size": 8, 'right': True, 'text_wrap': True})
        bold_border = workbook.add_format({'left': True, 'right': True, 'top': True, 'bottom': True, "bold": True,
                                           "font_size": 8, 'valign': 'top'})
        bold_border_wrap = workbook.add_format({'left': True, 'right': True, 'top': True, 'bottom': True, "bold": True,
                                           "font_size": 8, 'valign': 'top', 'text_wrap': True})
        normal_border = workbook.add_format(
            {'left': True, 'right': True, 'bottom': True, "font_size": 8, 'align': 'vcenter'})
        normal_border_wrap = workbook.add_format(
            {'left': True, 'right': True, 'bottom': True, "font_size": 8, 'align': 'vcenter', 'text_wrap': True})
        font_8 = workbook.add_format({"font_size": 8})
        border = workbook.add_format({'left': True, 'right': True, 'bottom': True, 'top': True})
        border_right_sub_head = workbook.add_format({'right': True, 'left': True, "bold": True, "font_size": 8})
        right_border = workbook.add_format({'right': True})
        bottom_right_border = workbook.add_format({'bottom': True, 'right': True})
        sheet.merge_range("A1:J1", "Export Invoice", heading)
        sheet.merge_range("A2:J2", '"SUPPLY MEANT FOR EXPORT UNDER LUT, WITHOUT PAYMENT OF INTEGRATED TAX (IGST) (ARN NO. AD090324210353H DT.29/03/2024)"', heading)
        sheet.merge_range('A3:E3', 'Manufacturer/Exporter:', border_right_sub_head)
        sheet.merge_range('F3:J3', 'Invoice No. & Date', border_right_sub_head)
        sheet.merge_range('C4:E7', 'PAN# : AADCS1781L', bold_border)
        sheet.merge_range('F4:J9', f"{self.name}    DATED    {self.date.strftime('%B %d, %Y')}", normal_border)
        sheet.merge_range("A8:B8", 'SURYA CARPET PVT. LTD.', font_8)
        sheet.merge_range("C9:E9", 'IEC # : 1588000311', bold_border)
        sheet.merge_range("A10:B10", 'UGAPUR, AURAI-221301', font_8)
        sheet.merge_range('F10:J10', "Buyer's Order No & Date", border_right_sub_head)
        sheet.merge_range('F11:J15', f"{self.buyer_order_no}    DATED    {self.buyer_order_date.strftime('%B %d, %Y')}", normal_border)
        sheet.merge_range("C11:E11", ' GSTIN # : 09AADCS1781L1ZY', bold_border)
        sheet.merge_range('A15:B15', 'BHADOHI (U.P.)', font_8)
        sheet.merge_range('F16:J16', f"END USE: GNX 100", heading)
        sheet.merge_range('A19:B19', 'INDIA', font_8)
        sheet.merge_range('F20:J21', f"Other Reference: {self.other_reference}", bold_border)
        sheet.merge_range('A4:B7', '')
        sheet.merge_range('C8:E8', '')
        sheet.merge_range('C10:E10', '')
        sheet.merge_range('A11:B14', '')
        sheet.merge_range('C12:E21', '')
        sheet.merge_range('A16:B18', '')
        sheet.merge_range('A20:B21', '')
        sheet.merge_range('A9:B9', '')
        sheet.merge_range('F17:J19', '', right_border)
        sheet.merge_range('A22:J22', '', bottom_right_border)
        sheet.merge_range('A23:B23', 'Consignee :', bold_border)
        sheet.merge_range('C23:E23', 'Buyer :', bold_border)
        sheet.merge_range('F23:J27', '', bold_border)
        sheet.merge_range('A24:B25', self.partner_id.name, font_8)
        sheet.merge_range('A26:B27', self.partner_id.street, font_8)
        sheet.merge_range('A28:B28', f"{self.partner_id.city}, {self.partner_id.state_id.code}-{self.partner_id.zip}", font_8)
        sheet.merge_range('A29:B29', 'USA' if self.partner_id.country_id.code == 'US' else self.partner_id.country_id.code, font_8)
        sheet.merge_range('A30:B32', f"TEL: {self.partner_id.mobile}", font_8)
        sheet.merge_range('A33:B33', f"E:{self.partner_id.email}", font_8)
        sheet.merge_range('C24:E33', f"{self.partner_id.name} {self.partner_id.street} {self.partner_id.city}, "
                                     f"{self.partner_id.state_id.code}-{self.partner_id.zip} {self.partner_id.phone} "
                                     f"email:{self.partner_id.email}", normal_border_wrap)
        sheet.merge_range('F28:G29', 'Country of Origin of Goods', bold_border)
        sheet.merge_range('H28:J29', 'Country of Final Destination', bold_border)
        sheet.merge_range('F30:G31', 'INDIA', heading2)
        sheet.merge_range('H30:J31', 'USA' if self.partner_id.country_id.code == 'US' else self.partner_id.country_id.code, heading2)
        sheet.merge_range('F32:J33', 'Terms of Delivery and Payment', bold_border)
        sheet.merge_range('F34:J36', 'F.O.B.', normal_border)
        sheet.merge_range('F37:J39', 'D.P.', normal_border)
        sheet.merge_range('A34:B34', 'Pre-Carriage By', bold_border)
        sheet.merge_range('C34:E34', 'Place of Receipt by Pre-carrier', bold_border)
        sheet.merge_range('A35:B35', self.pre_carriage_by, normal_border)
        sheet.merge_range('C35:E35', self.place_of_receipt, normal_border)
        sheet.merge_range('A36:B36', 'Vessel/Flight No.', bold_border)
        sheet.merge_range('C36:E36', 'Port of Loading', bold_border)
        sheet.merge_range('A37:B37', f"By {self.transportation_type.upper()}", normal_border)
        sheet.merge_range('C37:E37', self.port_of_loading, normal_border)
        sheet.merge_range('A38:B38', 'Port Of Discharge', bold_border)
        sheet.merge_range('C38:E38', 'Final Destination', bold_border)
        sheet.merge_range('A39:B39', self.port_of_discharge, normal_border)
        sheet.merge_range('C39:E39', f"{self.partner_id.city}, {self.partner_id.state_id.code}"
                                            f" ({'USA' if self.partner_id.country_id.code == 'US' else self.partner_id.country_id.code})", normal_border)
        sheet.merge_range('A40:C40', 'Marks & Nos./Container No.', bold_border)
        sheet.merge_range('D40:G40', 'Description of Goods', bold_border)
        sheet.write('H40', 'Quantity', bold_border)
        sheet.write('I40', 'Rate', bold_border)
        sheet.write('J40', 'Amount', bold_border)
        sheet.merge_range('A41:C43', self.partner_id.name, normal_border)
        sheet.merge_range('A44:C44', 'No. And Kinds of Pkgs.', bold_border)
        sheet.merge_range('A45:C47', f"{len(set(self.pack_invoice_line_ids.mapped('roll_no')))}", normal_border)
        sheet.merge_range('D41:G47', self.description_of_goods, normal_border_wrap)
        sheet.merge_range('H41:H49', '', normal_border)
        sheet.merge_range('I41:I49', '', normal_border)
        sheet.merge_range('J41:J49', '', normal_border)
        sheet.merge_range('A48:G48', 'Roll Nos:', bold_border)
        sheet.merge_range('A49:G49', f"1 - { len(set(self.pack_invoice_line_ids.mapped('roll_no')))}", normal_border)
        sheet.merge_range('A50:B51', 'Design / Quality', bold_border_wrap)
        sheet.merge_range('C50:C51', 'ITC HS CODE NO.', bold_border_wrap)
        sheet.merge_range('D50:D51', 'Knots/Sq.Mtr.', bold_border_wrap)
        sheet.merge_range('E50:E51', 'Total Area Sq.Mtr.', bold_border_wrap)
        sheet.merge_range('F50:F51', 'Price Per Sq.Mtr.', bold_border_wrap)
        sheet.merge_range('G50:G51', 'Total Pieces', bold_border_wrap)
        sheet.merge_range('H50:H51', 'Total Area Sq.Feet', bold_border_wrap)
        sheet.merge_range('I50:I51', 'Price Per Sq.Feet USD(F.O.B.)', bold_border_wrap)
        sheet.merge_range('J50:J51', 'Total Amount USD(F.O.B.)', bold_border_wrap)
        count = 52
        inv_group_data = self.prepare_invoice_data()
        for rec in inv_group_data:
            sheet.set_row(count, 12)
            sheet.merge_range(f"A{count}:B{count}", rec.get('design'), wrap_data)
            sheet.write(f'C{count}', rec.get('itch'), wrap_data)
            sheet.write(f'D{count}', rec.get('knots'), wrap_data)
            sheet.write(f'E{count}', rec.get('area_sq_mt'), zero2)
            sheet.write(f'F{count}', rec.get('rate_sq_mt'), zero5)
            sheet.write(f'G{count}', rec.get('total_pcs'), wrap_data)
            sheet.write(f'H{count}', rec.get('area_sq_feet'), zero3)
            sheet.write(f'I{count}', rec.get('rate_sq_ft'), zero2)
            sheet.write(f'J{count}', rec.get('amount'), zero2)
            count += 1

        amount = round(sum([rec.get('amount') for rec in inv_group_data]), 2)
        sheet.merge_range(f'A{count}:C{count}', '', bold_border)
        sheet.write(f'D{count}', 'TOTAL-', bold_border)
        sheet.write(f"E{count}", round(sum([rec.get('area_sq_mt') for rec in inv_group_data]), 2), bold_border_zero2)
        sheet.write(f"F{count}", '', bold_border)
        sheet.write(f"G{count}", sum([int(rec.get('total_pcs')) for rec in inv_group_data]), bold_border)
        sheet.write(f"H{count}", round(sum([rec.get('area_sq_feet') for rec in inv_group_data]),3), bold_border_zero3)
        sheet.write(f"I{count}", '', bold_border)
        sheet.write(f"J{count}", amount, bold_border_zero2)
        count+=1

        sheet.merge_range(f'A{count}:G{count}', '', bold_border)
        sheet.merge_range(f'H{count}:I{count}', 'Total Amount Before Tax', bold_border)
        sheet.write(f'J{count}', amount, bold_border_zero2)
        count+=1

        sheet.merge_range(f'A{count}:G{count}', '', bold_border)
        sheet.merge_range(f'H{count}:I{count}', 'Add: IGST', bold_border)
        sheet.write(f'J{count}', '0.00', bold_border)
        count += 1

        sheet.set_row(count-1, 20)
        sheet.merge_range(f'A{count}:B{count}', 'Amount Chargabe (in words):  US$', normal_border_wrap)
        sheet.merge_range(f'C{count}:G{count}', num2words(float(amount), lang='en', to='currency').replace('and', '').replace('euro,', 'and')+' Only', bold_border_wrap)
        sheet.merge_range(f'H{count}:I{count}', 'Total Amount After Tax-', bold_border)
        sheet.write(f'J{count}', amount, bold_border_zero2)
        count += 1

        sheet.merge_range(f'A{count}:J{count}', '', bold_border)
        count += 1

        sheet.merge_range(f'A{count}:J{count+1}', 'WEIGHT DETAILS :', bold_border)
        count += 2

        sheet.merge_range(f'A{count}:J{count}', f'Gross Weight : {self.gross_weight} Kgs.', normal_border)
        count += 1

        sheet.merge_range(f'A{count}:J{count}', f'Net Weight : {self.net_weight} Kgs.', normal_border)
        count += 1

        sheet.set_row(count, 80)
        sheet.merge_range(f'A{count}:D{count+1}', '', bold_border)
        sheet.merge_range(f'E{count}:J{count}', 'Declaration :', bold_border)
        sheet.merge_range(f"E{count+1}:J{count+1}", '1. We intend to claim rewards under RoDTEP Scheme..\n'
                                                  '2. We abide by provisional of foreign exchange management Act regarding realization. \n'
                                                  '3. “SUPPLY MEANT FOR EXPORT UNDER LUT WITHOUT PAYMENT OF  INTEGRATED TAX (IGST)” \n'
                                                  '4. We declare that this invoice shows the actual price of the  goods described and all particulars are true and correct', normal_border_wrap)

        workbook.close()
        file_data.seek(0)
        attachment = self.env['ir.attachment'].create({
            'name': f"Export Invoice Excel", 'type': 'binary',
            'datas': base64.b64encode(file_data.getvalue()).decode(), 'mimetype': 'application/vnd.ms-excel',
            'res_model': 'inno.packaging.invoice', 'res_id': self.id})
        self.message_post(body="<b>Product Planning report</b>", attachment_ids=[attachment.id])

    def prepare_invoice_data(self):
        invoice_group_data = list()
        for rec in self.pack_invoice_line_ids.mapped('invoice_group'):
            group_data = self.pack_invoice_line_ids.filtered(lambda pil: pil.invoice_group.id == rec.id)
            area_sq_mt = round(
                sum([rec.product_id.product_template_attribute_value_ids.product_attribute_value_id.size_id.area_sq_mt
                     for rec in group_data]), 2)
            area_sq_yard = round(
                sum([rec.product_id.product_template_attribute_value_ids.product_attribute_value_id.size_id.area for rec
                     in group_data]), 2)
            amount = round(sum([rec.amount for rec in group_data]), 2)
            rate_sq_mt = round(float(amount) / float(area_sq_mt), 5)
            rate_sq_ft = round(float(amount) / float(area_sq_yard), 3)
            invoice_group_data.append({'design': rec.name, 'itch': rec.hsn_code, 'knots': rec.knots if rec.knots > 0 else '-',
                                       'area_sq_mt': area_sq_mt, 'total_pcs': group_data.__len__(),
                                       'area_sq_feet': area_sq_yard, 'rate_sq_mt': rate_sq_mt,
                                       'amount': amount, 'rate_sq_ft': rate_sq_ft})
        return invoice_group_data

    def generate_master_key(self):
        file_data = BytesIO()
        workbook = xlsxwriter.Workbook(file_data, {})
        sheet = workbook.add_worksheet("Master Key")
        heading = workbook.add_format({"bold": True, "font_size": 10, 'font_color': 'red'})
        heading2 = workbook.add_format({"bold": True, "font_size": 10, 'font_color': 'red', 'bg_color': 'yellow', 'left': True})
        money = workbook.add_format({'num_format': '#,##0.00', 'left': True, 'right': True, 'top': True, 'bottom': True})
        border = workbook.add_format({'left': True, 'right': True, 'top': True, 'bottom': True})
        sheet.merge_range("A1:K1", f"MASTER KEY OF INVOICE NO. {self.name} DATED , {self.date.strftime('%B %d, %Y')} "
                                   f"ONE 40' HC CONTAINER", heading)
        sheet.set_column('A:A', 22)
        sheet.set_column('B:B', 15)
        sheet.set_column('C:C', 22)
        sheet.set_column('D:D', 15)
        sheet.set_column('E:E', 12)
        sheet.set_column('F:F', 12)
        sheet.set_column('G:G', 10)
        sheet.set_column('H:H', 12)
        sheet.set_column('I:I', 60)

        sheet.write('A2', '', heading2)
        sheet.write('B2', '', heading2)
        sheet.write('C2', '', heading2)
        sheet.write('D2', '', heading2)
        sheet.write('E2', '', heading2)
        sheet.write('F2', '', heading2)
        sheet.write('G2', 'RATE', heading2)
        sheet.write('H2', 'TOTAL', heading2)
        sheet.write('I2', 'Roll No.', heading2)

        sheet.write('A3', '', heading2)
        sheet.write('B3', '', heading2)
        sheet.write('C3', '', heading2)
        sheet.write('D3', '', heading2)
        sheet.write('E3', '', heading2)
        sheet.write('F3', '', heading2)
        sheet.write('G3', 'PER', heading2)
        sheet.write('H3', 'VALUE', heading2)
        sheet.write('I3', '', heading2)

        sheet.write('A4', 'PO NOS.', heading2)
        sheet.write('B4', 'ITEM NO', heading2)
        sheet.write('C4', 'BUYER ITEM CODE', heading2)
        sheet.write('D4', 'DESIGN NOS.', heading2)
        sheet.write('E4', 'SIZE (SQ.FTS)', heading2)
        sheet.write('F4', 'NO.OF PCS.', heading2)
        sheet.write('G4', 'PIECE', heading2)
        sheet.write('H4', 'US$', heading2)
        sheet.write('I4', '', heading2)

        sheet.write('A5', '', heading2)
        sheet.write('B5', '', heading2)
        sheet.write('C5', '', heading2)
        sheet.write('D5', '', heading2)
        sheet.write('E5', '', heading2)
        sheet.write('F5', '', heading2)
        sheet.write('G5', '', heading2)
        sheet.write('H5', '', heading2)
        sheet.write('I5', '', heading2)

        count = 6
        for product in self.pack_invoice_line_ids.product_id:
            sale_ids = self.pack_invoice_line_ids.filtered(lambda pl: pl.product_id.id == product.id).sale_order_id.ids
            sale_ids.append(False)
            for sale in sale_ids:
                act_data = self.pack_invoice_line_ids.filtered(lambda pl: pl.product_id.id == product.id and pl.sale_order_id.id == sale)
                if act_data:
                    amount = sum([rec.amount for rec in act_data])
                    sheet.write(f'A{count}', act_data.sale_order_id.order_no if act_data.sale_order_id else 'Sample', border)
                    sheet.write(f'B{count}', act_data.product_id.default_code, border)
                    sheet.write(f'C{count}', act_data.product_id.default_code, border)
                    sheet.write(f'D{count}', act_data.product_id.name, border)
                    sheet.write(f'E{count}', act_data.product_id.product_template_attribute_value_ids.product_attribute_value_id.name, border)
                    sheet.write(f'F{count}', act_data.__len__(), border)
                    sheet.write(f'G{count}', amount/act_data.__len__(), money)
                    sheet.write(f'H{count}', amount, money)
                    sheet.write(f'I{count}', ', '.join([str(rec.roll_no) for rec in act_data]), border)
                    count += 1

        sheet.write(f'E{count}', 'Total', border)
        sheet.write(f'F{count}', self.pack_invoice_line_ids.__len__(), border)
        sheet.write(f'G{count}', '', border)
        sheet.write(f"H{count}", sum([rec.amount for rec in self.pack_invoice_line_ids]), money)


        workbook.close()
        file_data.seek(0)
        attachment = self.env['ir.attachment'].create({
            'name': f"Master Key", 'type': 'binary',
            'datas': base64.b64encode(file_data.getvalue()).decode(), 'mimetype': 'application/vnd.ms-excel',
            'res_model': 'inno.packaging.invoice', 'res_id': self.id})
        self.message_post(body="<b>Product Planning report</b>", attachment_ids=[attachment.id])

    def update_rate(self):
        for rec in self.pack_invoice_line_ids.filtered(lambda pl: pl.rate_update > 0):
            self.message_post(body=f"Rate Update from {rec.rate} {rec.rate_update} for roll no {rec.roll_no} and bale no: {rec.bale_no}")
            rec.write({'rate': rec.rate_update, 'rate_update': 0})


class PackagingInvoiceLine(models.Model):
    _name = 'inno.packaging.invoice.line'

    packing_id = fields.Many2one(comodel_name='inno.packaging.invoice')
    product_id = fields.Many2one(comodel_name='product.product', string='Product')
    bale_no = fields.Char(string='Bale No')
    roll_no = fields.Integer(string="Roll No")
    invoice_group = fields.Many2one(comodel_name="inno.invoive.group", string='Invoice Group')
    qty = fields.Float(digits=(10, 3), string="Qty")
    deal_qty = fields.Float(digits=(10, 3), string="Deal Qty")
    rate = fields.Float(digits=(10, 3), string="Rate")
    amount = fields.Float(digits=(10, 3), string="Amount", compute='_compute_amount')
    net_weight = fields.Float(digits=(10, 3))
    gross_weight = fields.Float(digits=(10, 3))
    sale_order_id = fields.Many2one(comodel_name='sale.order')
    related_so = fields.Char(string='Related SO')
    rate_update = fields.Float(digits=(10, 3), string='Rate Update')

    def _compute_amount(self):
        for rec in self:
            rec.amount = rec.deal_qty*rec.rate
