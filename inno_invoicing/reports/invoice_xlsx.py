import datetime
from odoo import models, api


class ReportInvoice(models.AbstractModel):
    _name = 'report.inno_invoicing.report_print_invoice_xlx'
    _inherit = "report.report_xlsx.abstract"

    # def generate_xlsx_report(self, workbook, data, invoice):
    #     sheet = workbook.add_worksheet('Export Invoice')
    #     bold = workbook.add_format({'bold': True, 'align': 'center', 'bg_color': '#fffbed', 'border': True})
    #     title = workbook.add_format(
    #         {'bold': True, 'align': 'center', 'font_size': 20, 'bg_color': '#f2eee4', 'border': True})
    #     header_row_style = workbook.add_format({'bold': True, 'align': 'center', 'border': True})
    #     wrap_format = workbook.add_format({'text_wrap': True})
    #     cell_format = workbook.add_format(
    #         {'font_size': '12px', 'align': 'center'})
    #     # merge_format = workbook.add_format({
    #     #     'bold': True,
    #     #     # 'border': 6,
    #     #     'align': 'center',
    #     #     'valign': 'vcenter',
    #     #     # 'fg_color': '#D7E4BC',
    #     # })
    #     #
    #     # sheet.merge_range('B3:D7', 'Merged Cells')
    #     # sheet.insert_textbox('B2', 'Welcome to Tutorialspoint',
    #     #                   {'border': {'color': '#FF9900'}})
    #     #
    #     # sheet.insert_textbox('B10', 'Welcome to Tutorialspoint', {
    #     #     'line':
    #     #         {'color': 'blue', 'dash_type': 'dash_dot'}
    #     # })
    #
    #     # sheet.merge_range('A2:F2', 'Export Invoice', title)
    #     row = 3
    #     col = 0
    #     sheet.set_column(0, 5, 18)
    #     sheet.write(3, 0, "Manufacturer / Exporter :", bold)
    #     # sheet.merge_range("A1:M1",'PACKING LIST', title)
    #     sheet.write(3,0,"Manufacturer / Exporter :", bold)
    #     sheet.write(3, 3, "REX NUMBER: ", bold)
    #     sheet.write(3, 4, "Invoice No & Date: ", bold)
    #     sheet.write(4, 0, "( HEAD OFFICE ) :", bold)
    #     sheet.write(4, 3, "INREX1588000311DG015", bold)
    #     sheet.write(4, 4, "SCP424/23-24  DATED  NOVEMBER 23, 2023", bold)
    #     sheet.write(4, 0, "SURYA CARPET PVT. LTD., UGAPUR, AURAI- 221301, BHADOHI, (U.P.), INDIA", bold)
    #     sheet.write(4, 4, "Buyer's Order No & Date", bold)
    #     sheet.write(5, 4, "PO 55 764662",)
    #     sheet.write(6, 0, "( BRANCH OFFICE ) :", bold)
    #     sheet.write(6, 0, "D-174, EPIP, SITE-V, KASNA, GREATER NOIDA, GAUTAM BUDDH NAGAR, (U.P.), 201310, INDIA",)
    #     sheet.write(7, 4, "Other Reference",)
    #     sheet.write(6, 0, "Consignee :",bold)
    #     sheet.write(6, 1, "Delivery Address :", bold)
    #     sheet.write(6, 2, "Buyer: (If Other than Consignee)", bold)
    #     sheet.write(6, 4, "1st Notify:", bold)
    #     sheet.write(6, 6, "2nd Notify::", bold)
    #     sheet.write(7, 0, "TJX EUROPE BUYING (DEUTSCHLAND) LIMITED \n"
    #                       " CLARENDON ROAD,WATFORD,HERTS WD17 1TX TJX VAT NUMBER \n"
    #                       ": DE 275586731",wrap_format)
    #     sheet.write(7, 1, "TJX UK c/o TJX Distribution Ltd & Co KG Ben-Cammarata Strasse 1 50126 Bergheim, GERMANY,", cell_format )
    #     sheet.write(7, 2, "SURYA CARPET INC.1 SURYA DRIVE, WHITE, GA-30184, U.S.A.TEL: 877-275-7847, FAX: 877-786-7847 EMAIL: RECEIVING@SURYA.COM, LEEANN.MCDOUGLE@surya.com",)
    #     sheet.write(7, 6, "SURYA CARPET INC. 1 SURYA DRIVE, WHITE, GA-30184, U.S.A. TEL: 877-275-7847, FAX: 877-786-7847 EMAIL: RECEIVING@SURYA.COM,LEEANN.MCDOUGLE@surya.com",)
    #     sheet.write(9, 6, "Country of Orgin of Goods", bold)
    #     sheet.write(10, 6, "INDIA",)
    #     sheet.write(9, 7, "Country of final Destination", bold)
    #     sheet.write(10, 7, "GERMANY", )
    #     sheet.write(12,0,'Pre-carriage by',bold )
    #     sheet.write(12, 1, 'Place of Receipt byPre-carrier',bold )
    #     sheet.write(13, 1, 'ICD CCLP DADRI', bold)
    #     sheet.write(12, 6, "Terms of Delivery and Payment", bold)
    #     sheet.write(13, 6, "F.O.B.",)
    #     sheet.write(13, 0, "Vessel/Flight No.",bold )
    #     sheet.write(14, 0, "BY SEA",)
    #     sheet.write(13, 1, "Port of Loading", bold)
    #     sheet.write(14, 1, "MUNDRA",)
    #     sheet.write(15, 0, "Port of Discharge", bold)
    #     sheet.write(16, 0, "HAMBURG",)
    #     sheet.write(15, 1, "Final Destination", bold)
    #     sheet.write(16, 1, "GERMANY", )
    #     sheet.write(20, 0, "Marks & Nos.", bold)
    #     sheet.write(21, 0, "Container No.SURYA", )
    #     sheet.write(20, 1, "Description of goods", bold)
    #     sheet.write(21, 1, "45 CARTONS Properly packed in new polytube and Cartoons.", )
    #     sheet.write(20, 2, "Marks & Nos.", bold)
    #     sheet.write(21, 2, "Container No.SURYA", )

    def add_company_header(self, row, sheet, company, bold):
        company_name = 'Innpage'
        address = f"Kasna Noida"
        country = 'India'
        if company_name:
            image_data = False
            sheet.insert_image(row, 1, 'logo.png', {'image_data': image_data, 'x_scale': 0.10, 'y_scale': 0.10})
            sheet.write(row + 2, 1, company_name, bold)
            sheet.write(row + 3, 1, address)
            sheet.write(row + 4, 1, country)

    def add_partner_address(self, row, col, sheet, partner, bold, shipping=True):
        partner_name = "Rishabh"
        address = f"Fzd UP"
        country = "INDIA"
        phone = "39846524795"
        if phone:
            sheet.write(row, col, "Invoicing and Shipping Address:", bold)
        sheet.write(row + 1, col, partner_name)
        sheet.write(row + 2, col, address)
        sheet.write(row + 3, col, country)
        sheet.write(row + 4, col, phone)
    #
    # def generate_xlsx_report(self, workbook, data, orders):
    #     orders = [4, 5]
    #     for order in orders:
    #         row = 1
    #         sheet = workbook.add_worksheet("INVOICE")
    #         bold = workbook.add_format({"bold": True})
    #         heading = workbook.add_format({"font_size": 18})
    #         date_style = workbook.add_format({'num_format': 'yyyy-mm-dd'})
    #         center_style = workbook.add_format({'valign': 'center', 'bold': True})
    #         wrap_text = workbook.add_format({'text_wrap': True})
    #         money = workbook.add_format({'num_format': '$#,##0.00'})
    #         white_bg = workbook.add_format({'bg_color': 'white'})
    #         bottom_border = workbook.add_format({'bottom': True})
    #         left_border = workbook.add_format({'left': True})
    #         success_cell = workbook.add_format({'left': True})
    #         company = "INNOAGE"
    #         partner = 4
    #         shipping_partner = "AYodya"
    #         self.add_company_header(row, sheet, company, bold)
    #         row += 6
    #         sheet.conditional_format("B8:E12", {'type': 'formula', 'criteria': 'True', 'format': white_bg})
    #         sheet.conditional_format("G8:J12", {'type': 'formula', 'criteria': 'True', 'format': white_bg})
    #         self.add_partner_address(row, 1, sheet, shipping_partner, bold)
    #         self.add_partner_address(row, 6, sheet, partner, bold, shipping=False)
    #         # row += 6
    #         sheet.write(2, 1, f"Quotation # S0001", heading)
    #         sheet.set_column("B:B", 30)
            # row += 1
            # sheet.write(row, 1, "Quotation Date:")
            # sheet.write(row, 3, "Salesperson:")
            # row += 1
            # sheet.write(row, 1, "01/03/04424", date_style)
            # sheet.write(row, 3, "s0001")
            # row += 2
            # sheet.merge_range(row, 1, row, 2, 'Description', bold)
            # sheet.write(row, 3, 'Quantity', center_style)
            # sheet.merge_range(row, 4, row, 5, 'Quantity Delivered', center_style)
            # sheet.merge_range(row, 6, row, 7, 'Quantity Invoiced', center_style)
            # sheet.merge_range(row, 8, row, 9, 'Unit Price', center_style)
            # sheet.write(row, 10, 'Amount', center_style)
            # row += 1
            # order =[4,5]
            # for line in order:
            #     sheet.merge_range(row, 1, row, 2, "HINDI", wrap_text)
            #     sheet.write(row, 3, "2", center_style)
            #     sheet.merge_range(row, 4, row, 5, line, center_style)
            #     sheet.merge_range(row, 6, row, 7, line, center_style)
            #     sheet.merge_range(row, 8, row, 9, line, money)
            #     sheet.write(row, 10, line, money)
            #     row += 1
            #
            # formula = f"=sum(K{row - 1}:K{row})"
            # row += 1
            # sheet.write(row, 10, formula, money)

            # sheet.conditional_format(f"A1:M{row + 4}", {'type': 'formula', 'criteria': 'True', 'format':False})
            # sheet.conditional_format(f"A{row + 4}:M{row + 4}",
            #                          {'type': 'formula', 'criteria': 'True', 'format': bottom_border})
            # sheet.conditional_format(f"N1:N{row + 4}", {'type': 'formula', 'criteria': 'True', 'format': left_border})


    def generate_xlsx_report(self, workbook, data, invoice):
        row = 1
        sheet = workbook.add_worksheet("EXPORT INVOICE")
        bold = workbook.add_format({"bold": True})
        heading = workbook.add_format({"font_size": 18})
        date_style = workbook.add_format({'num_format': 'yyyy-mm-dd'})
        center_style = workbook.add_format({'valign': 'center', 'bold': True})
        wrap_text = workbook.add_format({'text_wrap': True})
        money = workbook.add_format({'num_format': '$#,##0.00'})
        white_bg = workbook.add_format({'bg_color': 'white'})
        bottom_border = workbook.add_format({'bottom': True})
        left_border = workbook.add_format({'left': True})
        success_cell = workbook.add_format({'left': True})
        # sheet.Range["A2:P2"].merge_range()
        sheet.set_column('A:A', 15)
        sheet.set_column('B:B', 15)
        sheet.set_column('C:C', 20)
        sheet.set_column('D:D', 20)
        sheet.set_column('I:I', 15)
        sheet.set_column('J:J', 15)
        sheet.set_column('K:K', 15)
        sheet.merge_range("A2:K2",'EXPORT INVOICE',center_style)
        sheet.merge_range("A3:K3", '"SUPPLY MEANT FOR EXPORT UNDER LUT, WITHOUT PAYMENT OF INTEGRATED TAX (IGST) (ARN No. AD0903230551384 DT.31/03/2023)"', center_style)
        sheet.merge_range("A4:F4",'Manufacturer / Exporter :',bold)
        sheet.write(3, 6, "Invoice No & Date", bold)
        sheet.write(4, 0, "SURYA CARPET PVT. LTD.", )
        sheet.write(5, 0, "UGAPUR, AURAI-221301", )
        sheet.write(6, 0, "BHADOHI, (U.P.)")
        sheet.write(7, 0, "INDIA", )
        sheet.write(4, 6, "SCP341/23-24",) #po
        sheet.write(4, 7, "DATED  September  09, 2023", )  #po date
        sheet.write(5, 6, "Buyer's Order No & Date", )
        sheet.write(6, 6, "PO# 1900244   DATE  15.07.2023", )
        sheet.write(7, 6, "Other Reference", )
        sheet.write(8, 6, "END USE: GNX 100", bold)

        sheet.write(5, 3, "PAN #: AADCS1781L", bold)
        sheet.write(6, 3, "IEC #: 1588000311", bold)
        sheet.write(7, 3, "GSTIN #: 09AADCS1781L1ZY",bold )
        sheet.write(8, 3, "FEDEX A/C # 478480067",bold )

        sheet.write(9, 0, "Consignee :", bold)
        sheet.write(10, 0, "BENUTA GMBH,", bold)
        sheet.write(11, 0, "HOHE STR. 87, 53119 BONN,", bold)
        sheet.write(12, 0, "DEUTSCHLAND, GERMANY.", bold)
        sheet.write(13, 0, "TEL: 0049228969689", bold)

        sheet.write(9, 6, "Notify Party", bold)
        sheet.write(12, 6, "Country of Origin of Goods", bold)
        sheet.write(13, 6, "INDIA",)
        sheet.write(12, 9, "Country of Final Destination",bold )
        sheet.write(13, 9, "GERMANY",)

        sheet.write(14, 0, "ATTN.: HELEN NIETERS", bold)
        sheet.write(14, 6, "Terms of Delivery and Payment", bold)

        sheet.write(15, 0, "Pre-carriage by", bold)
        sheet.write(15, 3, "Place of Receipt by Pre-carrier",)
        sheet.write(15, 6, "C & F", )
        sheet.write(16, 6, "D.P.", )
        sheet.write(17, 6, "DAP ( DELIVERY AT PLACE )", )

        sheet.write(17, 0, "Vessel/Flight No.",bold )
        sheet.write(17, 3, "Port of Loading",bold )
        sheet.write(18, 1, "FEDEX COURIER",)

        sheet.write(19, 0, "Port of Discharge", bold)
        sheet.write(19, 3, "Final Destination", bold)

        sheet.write(20, 0, "ROTTARDAM",)
        sheet.write(20, 3, "GERMANY",)

        sheet.write(21, 0, "Marks & Nos./",bold )
        sheet.write(21, 3, "No. & Kinds of Pkgs. ", bold)
        sheet.write(21, 5, "Description of Goods", bold)
        sheet.write(22, 0, "Container No.", bold)
        sheet.write(22, 3, "2 ( Two )", bold)
        sheet.write(22, 5, "HAND WOVEN WOOLLEN CARPET.", bold)
        sheet.write(23, 3, "Rolls.",)

        sheet.write(24, 0, "Roll Nos:", bold)
        sheet.write(24, 3, "Properly Packed in new Polytube.",)
        sheet.write(25, 0, "1 TO 2", bold)

        sheet.set_row(27, 15)

        #table
        sheet.write(27, 0, "P.O.#", bold)
        sheet.write(27, 1, "ITEM", bold)
        sheet.write(27, 2, "COMPOSITION", bold)
        sheet.write(27, 3, "DESCRIPTION", bold)
        sheet.write(27, 4, " ITC HS CODE NO.", bold)
        sheet.write(27, 5, "Quantity  No. of PCS", bold)
        sheet.write(27, 6, "Quantity  No. of Rolls", bold)
        sheet.write(27, 7, "TOTAL AREA IN SQ.MTR.", bold)
        sheet.write(27, 8, "Net Wt. Kgs.", bold)
        sheet.write(27, 9, "PRICE PER SQ.MTR. C & F US$", bold)
        sheet.write(27, 10, "TOTAL AMOUNT US$ C & F", bold)
        ls = [6, 7]
        row =28

        for line in ls:
            sheet.write(row, 0, line, bold)
            sheet.write(row, 1, line, bold)
            sheet.write(row, 2, line, bold)
            sheet.write(row, 3, line, bold)
            sheet.write(row, 4, line, bold)
            sheet.write(row, 5, line, bold)
            sheet.write(row, 6,line, bold)
            sheet.write(row, 7, line, bold)
            sheet.write(row, 8, line, bold)
            sheet.write(row, 9, line, bold)
            sheet.write(row, 10, line, bold)
            row += 1
        row +=7
        sheet.write(row, 4, "TOTAL=", bold)
        sheet.write(row, 5, 28, bold)
        sheet.write(row, 6, 29, bold)
        sheet.write(row, 7, 25, bold)
        sheet.write(row, 8, 52, bold)
        sheet.write(row, 10, 520, bold)
        row +=1
        sheet.write(row, 8, "TOTAL AMOUNT BEFORE TAX", bold)
        sheet.write(row, 10, 520, bold)
        row += 1
        sheet.write(row, 8, "ADD: IGST", bold)
        sheet.write(row, 10, 0.0, bold)
        row += 1
        sheet.write(row, 8, "TOTAL AMOUNT AFTER TAX ", bold)
        sheet.write(row, 10, 520, bold)
        sheet.write(row, 8, "TOTAL AMOUNT AFTER TAX ", bold)
        sheet.write(row, 0, "Amount Chargeable (in word):",)
        sheet.write(row, 2, "US$ ONE HUNDRED FORTY SIX AND FORTY CENTS ONLY.",bold)
        row += 1
        sheet.write(row, 0, "WEIGHT DETAILS :", bold)
        row += 1
        sheet.write(row, 0, "Gross Weight :", bold)
        sheet.write(row, 1, "2886 kgh", bold)
        sheet.write(row, 3, "TOTAL BALES :", bold)
        sheet.write(row, 4, 2,)

        row += 1
        sheet.write(row, 0, "Nett Weight :", bold)
        sheet.write(row, 1, '24.800 KGS.',)
        sheet.write(row, 3, "TOTAL PIECES :", bold)
        sheet.write(row, 4, 2, )

        row += 1
        sheet.write(row, 0, "TOTAL CBM: ", bold)
        sheet.write(row, 1, '0.18 CBM', )
        sheet.write(row, 3, "TOTAL AREA SQ.MTR. :", bold)
        sheet.write(row, 4, 8, )


        row += 1
        sheet.write(row, 0, "Declaration:", bold)
        sheet.write(row, 7, "Signature & Date",)
        row += 1
        sheet.write(row, 0, "1. We intend to claim rewards under RoDTEP Scheme.", )
        row += 1
        sheet.write(row, 0, "2. We abide by provisional of foreign exchange management Act regarding realization.",)
        row += 1
        sheet.write(row, 0, "3. “SUPPLY MEANT FOR EXPORT UNDER LUT WITHOUT PAYMENT OF  INTEGRATED TAX (IGST)”",)
        row += 1
        sheet.write(row, 0, "4. We declare that this invoice shows the actual price of the goods described and all particulars are true and correct",)



        # company = "INNOAGE"
        # partner = 4
        # shipping_partner = "AYodya"
        # self.add_company_header(row, sheet, company, bold)
        # row += 6
        # sheet.conditional_format("B8:E12", {'type': 'formula', 'criteria': 'True', 'format': white_bg})
        # sheet.conditional_format("G8:J12", {'type': 'formula', 'criteria': 'True', 'format': white_bg})

