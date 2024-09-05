import datetime
from odoo import models, api


class ReportMaterialIssue(models.AbstractModel):
    _name = 'report.innorug_manufacture.report_print_material_allocation'
    _description = 'Will prepare the data for displaying the template.'

    @api.model
    def _get_report_values(self, docids, data=None):
        record = self.env['main.jobwork'].browse(docids)
        barcode_datas = self.get_barcode_list(record)
        config_id = self.env['inno.config'].sudo().search([], limit=1)
        abbr_dict = {'rectangular': '', 'circle': 'RD', 'corner': 'CO', 'cut': 'CU', 'hmt': 'HM', 'kidney': 'KD',
                     'octagon': 'OC', 'others': 'OT', 'oval': 'OV', 'shape': 'SH', 'shape_p': 'SH P',
                     'shape_r': 'SH R', 'square': '', 'star': 'ST'}

        products = [{
            'barcode': f"{data[1][0]}-{data[1][-1]}" if len(data[1]) > 1 else data[1][0],
            'design': data[0].product_id.product_tmpl_id.name,
            'size': f"{data[0].inno_mrp_size_id.name}{abbr_dict.get(data[0].product_id.inno_finishing_size_id.size_type)}",
            'pcs': len(data[1]),
            'area': f"{round(data[0].area * len(data[1]), 3)} {data[0].uom_id.name}", 'rate': data[0].rate, 'inc': '-',
            'po_no': data[0].mrp_work_order_id.sale_id.order_no, 'inc': data[0].incentive
        } for data in barcode_datas]
        material = dict()
        for rec in record.main_jobwork_components_lines:
            if rec.product_id.id in material.keys():
                material.get(rec.product_id.id).update(
                    {'quantity': material.get(rec.product_id) + rec.alloted_quantity})
            else:
                shade = rec.product_id.product_template_attribute_value_ids.filtered(
                    lambda al: al.attribute_id.name in ['shade', 'Shade', 'SHADE'])
                material[rec.product_id.id] = {
                    'product_name': rec.product_id.name,
                    'shade': shade[0].name if shade else 'N/A',
                    'qty': rec.alloted_quantity,
                    'cancel_qty': 'to_update',
                    'net_req_qty': 'to_update'
                }
        data = {'company': {'company_name': record.company_id.name, 'logo': record.company_id.logo,
                            'address_line1': f"{record.company_id.street}, {record.company_id.street}-"
                                             f"{record.company_id.zip}",
                            'address_line2': f"{record.company_id.city}, ({record.company_id.state_id.code}),"
                                             f"{record.company_id.country_id.name}",
                            'mobile': record.company_id.mobile, 'gstin': record.company_id.vat,
                            'state_code': record.company_id.state_id.code
                            },
                'subcontractor': {'name': record.subcontractor_id.name, 'address': record.subcontractor_id.street,
                                  'order_no': record.reference, 'remarks': record.remarks,
                                  'pcs' : 'no' if record.jobwork_line_ids[0].uom_id.id == record.jobwork_line_ids[0].product_id.uom_id.id else 'yes',
                                  'time_panality': record.time_penalty,
                                  'small_chunk': config_id.fragment_penalty, 'quality': ', '.join(
                        record.jobwork_line_ids.product_id.product_tmpl_id.quality.mapped('name')),
                                  'city': record.subcontractor_id.city, 'date': record.issue_date.strftime('%d/%m/%Y'),
                                  'contact_no': record.subcontractor_id.mobile or 'N/A', 'issue_by': self.env.user.name,
                                  'due_date': record.expected_received_date.strftime('%d/%m/%Y'),
                                  'aadhar_no': record.subcontractor_id.aadhar_no or 'N/A'},
                'products': {'data': products, 'total_pcs': sum(record.jobwork_line_ids.mapped('product_qty')),
                             'cancel_pcs': 0, 'total_area': sum(record.jobwork_line_ids.mapped('total_area')),
                             'lagat': record.jobwork_line_ids[0].product_id.product_tmpl_id.quality.weight,
                             'uom': record.jobwork_line_ids[0].uom_id.name},
                'material': material.values(),
                'total_materials': sum(map(lambda mat: mat.get('qty'), material.values())),
                'designs': record.jobwork_line_ids.mapped('product_id').mapped('image_1920'),
                'site': 'Main',
                'division': record.jobwork_line_ids.product_id[0].product_tmpl_id.division_id.name if
                record.jobwork_line_ids.product_id else 'N/A'
                }
        return {
            'doc_ids': docids,
            'doc_model': 'main.jobwork',
            'docs': record,
            'data': data}

    def get_barcode_list(self, record):
        barcodes = []
        for rec in record.jobwork_line_ids:
            jobwork = False
            temp_bcode = []
            prev_bcode = False
            for bcode in rec.barcodes:
                if not temp_bcode:
                    temp_bcode.append(bcode.name)
                    prev_bcode = int(bcode.name)
                    jobwork = rec
                elif int(bcode.name) == prev_bcode + 1:
                    temp_bcode.append(bcode.name)
                    prev_bcode = int(bcode.name)
                else:
                    barcodes.append([jobwork, temp_bcode])
                    temp_bcode = []
                    prev_bcode = False
                    temp_bcode.append(bcode)
                    prev_bcode = int(bcode.name)
                    jobwork = rec
            if temp_bcode:
                barcodes.append([jobwork, temp_bcode])
        return barcodes
