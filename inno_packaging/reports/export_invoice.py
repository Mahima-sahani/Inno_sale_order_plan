import datetime
from odoo import models, api
from num2words import num2words


class ReportExportInvoice(models.AbstractModel):
    _name = 'report.inno_packaging.report_print_inno_export_invoice'
    _description = 'Will prepare the data for displaying the template.'

    @api.model
    def _get_report_values(self, docids, data=None):
        records = self.env['inno.packaging.invoice'].browse(docids)
        invoice_group_data = list()
        for rec in records.pack_invoice_line_ids.mapped('invoice_group'):
            group_data = records.pack_invoice_line_ids.filtered(lambda pil: pil.invoice_group.id == rec.id)
            area_sq_mt = str(round(sum([rec.product_id.product_template_attribute_value_ids.product_attribute_value_id.size_id.area_sq_mt for rec in group_data]), 2))
            split_len = area_sq_mt.split('.')[1].__len__()
            if split_len < 2:
                area_sq_mt = area_sq_mt+'0'*(2-split_len)
            area_sq_yard = str(round(sum([rec.product_id.product_template_attribute_value_ids.product_attribute_value_id.size_id.area for rec in group_data]), 2))
            split_len = area_sq_yard.split('.')[1].__len__()
            if split_len < 3:
                area_sq_yard = area_sq_yard + '0' * (3 - split_len)
            amount = str(round(sum([rec.amount for rec in group_data]), 2))
            split_len = amount.split('.')[1].__len__()
            if split_len < 2:
                amount = amount + '0' * (2 - split_len)
            rate_sq_mt = str(round(float(amount)/float(area_sq_mt), 5))
            split_len = rate_sq_mt.split('.')[1].__len__()
            if split_len < 4:
                rate_sq_mt = rate_sq_mt + '0' * (4 - split_len)
            rate_sq_ft = str(round(float(amount)/float(area_sq_yard), 2))
            split_len = rate_sq_ft.split('.')[1].__len__()
            if split_len < 2:
                rate_sq_ft = rate_sq_ft + '0' * (2 - split_len)
            invoice_group_data.append({'design': rec.name, 'itch': rec.hsn_code, 'knots': rec.knots,
                                       'area_sq_mt': area_sq_mt, 'total_pcs': group_data.__len__(),
                                       'area_sq_feet': area_sq_yard, 'rate_sq_mt': rate_sq_mt,
                                       'amount': amount, 'rate_sq_ft': rate_sq_ft})
        total_amount = str(round(sum([float(rec.get('amount')) for rec in invoice_group_data]), 2))
        split_len = total_amount.split('.')[1].__len__()
        if split_len < 2:
            total_amount = total_amount + '0' * (2 - split_len)
        

        
        # CONVERT TOTAL AMOUNT INTO WORDS
        
        # amount_in_words = num2words(float(total_amount), lang='en', to='currency').capitalize().replace(' and',' ').replace(',',' ').replace('euro',' ').replace('-',' ')+' Only'
        amt = str(total_amount)
        split = amt.split('.')
        before_dec = float(split[0])
        after_dec = float(split[1])
        fc = num2words(before_dec, lang='en', to='currency')
        fl = num2words(after_dec, lang='en', to='currency')
        before_dec = fc.capitalize().replace('-',' ').replace(',',' ').replace(' and',' ').replace(' zero',' ').replace(' cents',' ').replace(' euro',' ')
        after_dec = fl.replace('-',' ').replace('euro',' ').replace(' zero',' ').replace(',',' ')        
        amount_in_words = f"{before_dec} and {after_dec} only"
        
        total_mt_sq = str(round(sum([float(rec.get('area_sq_mt')) for rec in invoice_group_data]), 2))
        split_len = total_mt_sq.split('.')[1].__len__()
        if split_len < 2:
            total_mt_sq = total_mt_sq + '0' * (2 - split_len)
        total_sq_ft = str(round(sum([float(rec.get('area_sq_feet')) for rec in invoice_group_data]), 3))
        split_len = total_sq_ft.split('.')[1].__len__()
        if split_len < 3:
            total_sq_ft = total_sq_ft + '0' * (3 - split_len)
            records.write({'total_area' : total_sq_ft})
        gross_weight = str(round(records.gross_weight, 3))
        split_len = gross_weight.split('.')[1].__len__()
        if split_len < 3:
            gross_weight = gross_weight + '0' * (3 - split_len)
        net_weight = str(round(records.net_weight, 3))
        split_len = net_weight.split('.')[1].__len__()
        if split_len < 3:
            net_weight = net_weight + '0' * (3 - split_len)
        export_data = {'inv_name': records.name, 'inv_date': records.date.strftime('%B %d, %Y'),
                       'order_no': records.buyer_order_no, 'order_date': records.buyer_order_date.strftime('%B %d, %Y'),
                       'other_ref': records.other_reference, 
                       'partner_info':{
                           'name': records.partner_id.name, 'street': records.partner_id.street,
                            'city': f"{records.partner_id.city}, {records.partner_id.state_id.code}-{records.partner_id.zip}",
                            'country': 'USA' if records.partner_id.country_id.code == 'US' else records.partner_id.country_id.code,
                            'mobile': records.partner_id.mobile,
                            'email': records.partner_id.email
                            },
                        'consignee_info':{
                           'name': records.consignee_id.name, 'street': records.consignee_id.street,
                            'city': f"{records.consignee_id.city}, {records.consignee_id.state_id.code}-{records.consignee_id.zip}",
                            'country': 'USA' if records.consignee_id.country_id.code == 'US' else records.consignee_id.country_id.code,
                            'mobile': records.consignee_id.mobile,
                            'email': records.consignee_id.email
                            },
                       'pre_car_by': records.pre_carriage_by, 'pre_car_place': records.place_of_receipt,
                       'vessel': records.transportation_type.upper(), 'loading_port': records.port_of_loading,
                       'discharge_port': records.port_of_discharge,
                       'final_destination': f"{records.partner_id.city}, {records.partner_id.state_id.code}"
                                            f" ({'USA' if records.partner_id.country_id.code == 'US' else records.partner_id.country_id.code})",
                       'final_destination_country': 'USA' if records.partner_id.country_id.code == 'US' else records.partner_id.country_id.code,
                       'no_of_pack': len(set(records.pack_invoice_line_ids.mapped('roll_no'))),
                       'no_of_pack_in_words': num2words(len(set(records.pack_invoice_line_ids.mapped('roll_no'))), lang='en').title(),
                       'description_of_goods': records.description_of_goods,
                       'invoice_group_data': invoice_group_data,
                       'total_sq_mt': total_mt_sq,
                       'total_pcs': str(sum([int(rec.get('total_pcs')) for rec in invoice_group_data])),
                       'total_sq_ft': total_sq_ft,
                       'total_amount': total_amount,
                       'total_amount_in_words': amount_in_words,
                       'gross_weight': gross_weight,
                       'net_weight': net_weight,
                       }
        
        export_data['container_no'] = f"{records.consignee_id.job_worker_code} / {records.partner_id.job_worker_code}"

        return {
            'doc_ids': docids,
            'doc_model': 'mrp.barcode',
            'docs': records,
            'data': export_data,
            'company': self.env['res.company'].browse(1)
        }
