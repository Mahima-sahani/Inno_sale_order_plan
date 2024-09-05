import datetime
from odoo import models, api


class ReportMaterialIssue(models.AbstractModel):
    _name = 'report.inno_finishing.report_job_work_print_material_allocation'
    _description = 'Will prepare the data for displaying the template.'

    def check_area_units(self, record, jobwork):
        unit = {'sq_yard': 'Sq. Yard',
                'feet': 'Feet',
                'sq_feet': 'Sq. Feet',
                'choti': 'Sq. Meter', }
        lines =record.jobwork_barcode_lines.filtered(lambda code: code.product_id.id in jobwork.ids)
        return f"{round(sum([rec.total_area for rec in lines]),4)}{unit.get(record.jobwork_barcode_lines[0].unit)}"

    def check_total_area(self, record, jobwork):
        unit = {'sq_yard': 'Sq. Yard',
                         'feet': 'Feet',
                         'sq_feet': 'Sq. Feet',
                         'choti': 'Sq. Meter', }
        area = sum(record.jobwork_barcode_lines.mapped('total_area'))
        return f"{area}{unit.get(record.jobwork_barcode_lines[0].unit)}"

    @api.model
    def _get_report_values(self, docids, data=None):
        record = self.env['finishing.work.order'].browse(docids)
        prs = record.jobwork_barcode_lines.mapped('product_id')
        products = [{
            'barcode': ', '.join((record.jobwork_barcode_lines.filtered(
                lambda code: jobwork.id in code.product_id.ids)).barcode_id.mapped('name')),
            'design': jobwork.default_code, 'size': jobwork.inno_finishing_size_id.name,
            'pcs': len((record.jobwork_barcode_lines.filtered(lambda code: jobwork.id in code.product_id.ids))),
            'cancel_pcs': '-', 'area': self.check_area_units(record, jobwork),
            'color': jobwork.product_tmpl_id.color.name,
            'rate': record.jobwork_barcode_lines.filtered(lambda bl: bl.product_id.id in jobwork.ids)[0].rate,
            'inc': '-',
            'po_no': ', '.join(rec.order_no for rec in record.jobwork_barcode_lines.filtered(
                lambda code: code.product_id.id in jobwork.ids).barcode_id.sale_id),
        } for jobwork in prs]
        size = [{
            'size': jobwork.name,
            'qty': self.env['jobwork.barcode.line'].search_count(
                [('inno_finishing_size_id', '=', jobwork.id), ('finishing_work_id', '=', record.id)]),
        } for jobwork in record.jobwork_barcode_lines.inno_finishing_size_id]
        temp_len = len(size)
        lis1, lis2, lis3 = [], [], []
        while temp_len > 0:
            lis1.append(size.pop())
            temp_len -= 1
            if temp_len == 0:
                break
            lis2.append(size.pop())
            temp_len -= 1
            if temp_len == 0:
                break
            lis3.append(size.pop())
            temp_len -= 1
        material = dict()
        for rec in record.material_lines:
            if rec.product_id.id in material.keys():
                material.get(rec.product_id.id).update({'quantity': rec.product_qty})
            else:
                shade = rec.product_id.product_template_attribute_value_ids.filtered(
                    lambda al: al.attribute_id.name in ['shade', 'Shade', 'SHADE'])
                material[rec.product_id.id] = {
                    'product_name': rec.product_id.name,
                    'shade': shade[0].name if shade else 'N/A',
                    'qty': rec.product_qty,
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
                                  'order_no': record.name, 'pincode': record.subcontractor_id.zip,
                                  'city': record.subcontractor_id.city, 'date': datetime.datetime.today().date(),
                                  'contact_no': record.subcontractor_id.mobile or 'N/A',
                                  'code': record.subcontractor_id.job_worker_code,
                                  'due_date': record.expected_date, 'location': record.location_id.location_id.name,
                                  'aadhar_no': record.subcontractor_id.vat or 'N/A', 'issue_by': self.env.user.name
                                  },
                'products': {'data': products, 'total_pcs': len(record.jobwork_barcode_lines),
                             'cancel_pcs': 0, 'total_area': self.check_total_area(record, prs), 'size1': lis1,
                             'size2': lis2, 'size3': lis3,
                             'total_rate': round(sum([rec.total_area * rec.rate for rec in record.jobwork_barcode_lines]),2),
                             'lagat': 0.000, 'loss': 0.000},
                'material': material.values(),
                'designs': record.jobwork_barcode_lines.mapped('product_id').mapped('image_1920'),
                'site': "Main",
                'division': record.jobwork_barcode_lines.product_id[0].product_tmpl_id.division_id.name if
                record.jobwork_barcode_lines.product_id else 'N/A'
                }
        return {
            'doc_ids': docids,
            'doc_model': 'finishing.work.order',
            'docs': record,
            'data': data}

