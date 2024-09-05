import datetime
from odoo import models, api
from num2words import num2words


class ReportExportInvoice(models.AbstractModel):
    _name = 'report.inno_packaging.report_print_packaging_list'
    _description = 'Will prepare the data for packaging list'

    @api.model
    def _get_report_values(self, docids, data=None):
        records = self.env['inno.packaging.invoice'].browse(data.get('doc_ids'))
        invoice_group_data = list()
        roll_no = 1
        report_type = data.get('report_type')

        obj = sorted(records.pack_invoice_line_ids.mapped('roll_no'))
        set_obj = set(obj)
        list_obj = list(set_obj)
        
        if report_type == 'normal':
                temp_data = []
                for roll in sorted(list_obj):
                    for grp_data in records.pack_invoice_line_ids.mapped('invoice_group'):
                        group_data = records.pack_invoice_line_ids.filtered(lambda pil: pil.roll_no == roll and pil.invoice_group.id == grp_data.id  )
                        if group_data:
                            area_sq_yard = str(round(sum([rec.product_id.product_template_attribute_value_ids.product_attribute_value_id.size_id.area for rec in group_data]), 2))
                            split_len = area_sq_yard.split('.')[1].__len__()
                            if split_len < 3:
                                area_sq_yard = area_sq_yard + '0' * (3 - split_len)
                            temp_data.append({'design': group_data[0].product_id.name, 'total_pcs': group_data.__len__(), 'group': roll,
                                              'quality': grp_data.name, 'size': group_data[0].product_id.product_template_attribute_value_ids.product_attribute_value_id.name,
                                              'area_sq_feet': area_sq_yard, 'roll': roll_no})
                            roll_no += 1
                if temp_data:
                    total_area_sq_ft = str(round(sum([float(rec.get('area_sq_feet')) for rec in temp_data]), 3))
                    split_len = total_area_sq_ft.split('.')[1].__len__()
                    if split_len < 3:
                        total_area_sq_ft = records.total_area
                        # total_area_sq_ft = total_area_sq_ft + '0' * (3 - split_len)
                    invoice_group_data.append(
                        {'inv_data': temp_data, 'total_pcs': sum([rec.get('total_pcs') for rec in temp_data]),
                         'total_area': total_area_sq_ft})
        else:
            for rec in records.pack_invoice_line_ids.mapped('invoice_group'):
                temp_data = []
                for size in records.pack_invoice_line_ids.filtered(lambda pil: pil.invoice_group.id == rec.id).product_id.product_template_attribute_value_ids.product_attribute_value_id.size_id:
                    group_data = records.pack_invoice_line_ids.filtered(lambda pil: pil.invoice_group.id == rec.id and pil.product_id.product_template_attribute_value_ids.product_attribute_value_id.size_id.id == size.id)
                    # area_sq_yard = str(round(
                    #     sum([rec.product_id.product_template_attribute_value_ids.product_attribute_value_id.size_id.area
                    #          for rec in group_data]) * group_data.__len__(), 2))

                    area = [rec.product_id.product_template_attribute_value_ids.product_attribute_value_id.size_id.area for rec in group_data][0]
                    area_sq_yard = area * group_data.__len__()

                    # split_len = area_sq_yard.split('.')[1].__len__()
                    # if split_len < 3:
                    #     area_sq_yard = area_sq_yard + '0' * (3 - split_len)
                    temp_data.append(
                        {'total_pcs': group_data.__len__(), 'group': ', '.join(set([str(rec.roll_no) for rec in group_data].sort())),
                         'quality': rec.name, 'size': group_data[
                            0].product_id.product_template_attribute_value_ids.product_attribute_value_id.name,
                         'area_sq_feet': area_sq_yard, 'roll': roll_no})
                    roll_no += 1
                total_area_sq_ft = str(round(sum([float(rec.get('area_sq_feet')) for rec in temp_data]), 3))
                split_len = total_area_sq_ft.split('.')[1].__len__()
                if split_len < 3:
                    total_area_sq_ft = records.total_area
                    # total_area_sq_ft = total_area_sq_ft + '0' * (3 - split_len)
                invoice_group_data.append({'inv_data': temp_data, 'total_pcs': sum([rec.get('total_pcs') for rec in temp_data]),
                                       'total_area': total_area_sq_ft})
        grand_total_area_sq_ft = str(round(sum([float(rec.get('total_area')) for rec in invoice_group_data]), 3))
        split_len = grand_total_area_sq_ft.split('.')[1].__len__()
        if split_len < 3:
            # grand_total_area_sq_ft = grand_total_area_sq_ft + '0' * (3 - split_len)
            grand_total_area_sq_ft = records.total_area
        net_weight = str(round(records.net_weight, 3))
        split_len = net_weight.split('.')[1].__len__()
        if split_len < 3:
            net_weight = net_weight + '0' * (3 - split_len)
        gross_weight = str(round(records.gross_weight, 3))
        split_len = gross_weight.split('.')[1].__len__()
        if split_len < 3:
            gross_weight = gross_weight + '0' * (3 - split_len)

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
                       'invoice_group_data': invoice_group_data, 'net_weight': net_weight,
                       'total_pcs': str(sum([int(rec.get('total_pcs')) for rec in invoice_group_data])),
                       'total_sq_ft': grand_total_area_sq_ft, 'gross_weight': gross_weight,
                       'report_type': report_type
                       }
        export_data['container_no'] = f"{records.consignee_id.job_worker_code} / {records.partner_id.job_worker_code}"
        return {
            'doc_ids': docids,
            'doc_model': 'mrp.barcode',
            'docs': records,
            'data': export_data,
            'company': self.env['res.company'].browse(1)
        }
