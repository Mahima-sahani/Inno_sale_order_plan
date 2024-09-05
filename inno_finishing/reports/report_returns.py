import datetime
from odoo import models, api,fields


class ReportReturnReceived(models.AbstractModel):
    _name = 'report.inno_finishing.report_print_return'
    _description = 'Will prepare the data for displaying the template.'

    @api.model
    def _get_report_values(self, docids, data=None):
        record = self.env['finishing.work.order'].browse(docids)
        prs = record.return_barcode_lines.mapped('product_id')
        division_id = prs.mapped("division_id")
        products = [{
            'barcode': ', '.join(
                (record.return_barcode_lines.filtered(lambda code: jobwork.id in code.product_id.ids)).barcode_id.mapped(
                    'name')),
            'design': jobwork.default_code, 'size': jobwork.inno_finishing_size_id.name,
            'pcs': len((record.return_barcode_lines.filtered(lambda code: jobwork.id in code.product_id.ids))),
            'cancel_pcs': '-', 'area': sum(
                (record.return_barcode_lines.filtered(lambda code: jobwork.id in code.product_id.ids)).mapped('total_area')),
            'rate': record.return_barcode_lines.filtered(lambda code: jobwork.id in code.product_id.ids)[0].rate,
            'inc': '-',
            'po_no': False
        } for jobwork in prs]
        material = dict()
        picking_ids = self.env['stock.picking'].search([('finishing_work_id', '=', record.id),
                                                        ('origin', '=', f"Cancel/Main Job Work: {record.name}")], limit=1)
        if picking_ids:
            if (picking_ids.date).date() == fields.Datetime.today().date():
                for rec in picking_ids.move_ids_without_package:
                    if rec.product_id.id in material.keys():
                        material.get(rec.product_id.id).update({'quantity': material.get(rec.product_id) + float(rec.product_uom_qty)})
                    else:
                        material[rec.product_id.id] = {
                            'product_name': rec.product_id.name,
                            'shade': 'to update',
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
                                  'order_no': record.name, 'purja_no': "cost center",
                                  'city': record.subcontractor_id.city, 'date': datetime.datetime.today().date(),
                                  'contact_no': record.subcontractor_id.mobile or 'N/A',
                                  # 'due_date': record.expected_received_date,
                                  'aadhar_no': record.subcontractor_id.vat or 'N/A', 'issue_by': self.env.user.name
                                  },
                'products': {'data': products, 'total_pcs': len(record.return_barcode_lines),
                             'cancel_pcs': 0, 'total_area': sum(record.return_barcode_lines.mapped('total_area')),
                             'lagat': 0.000, 'loss': 0.000},
                'material': material.values(),
                'designs': record.return_barcode_lines.mapped('product_id').mapped('image_1920'),
                'site': "Main",
                'division': record.return_barcode_lines.product_id[0].product_tmpl_id.division_id.name if
                record.return_barcode_lines.product_id else 'N/A'
                }
        return {
            'doc_ids': docids,
            'doc_model': 'finishing.work.order',
            'docs': record,
            'data': data}