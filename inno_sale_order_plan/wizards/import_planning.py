from odoo import models, fields, _
from odoo.exceptions import UserError
import base64, xlrd
from datetime import datetime, timedelta


class ImportPlanning(models.TransientModel):
    _name = 'inno.import.planning'
    _description = 'Used to import planning records from xls file'

    file_name = fields.Char()
    data = fields.Binary(string='CSV File', required=True)
    re_plan_reason = fields.Text(string="Re-Planning Reason")

    def import_sale_planning(self):
        if self.file_name.split('.')[1] not in ['xlsx', 'xls']:
            raise UserError(_('You can only import xls or xlsx files'))
        file_contents = base64.b64decode(self.data)
        workbook = xlrd.open_workbook(file_contents=file_contents)
        sheet = workbook.sheet_by_index(0)
        sku_not_found = []
        records = []
        skus_added = []
        for row in range(1, sheet.nrows):
            customer_name = sheet.cell(row, 7).value
            order_date = sheet.cell(row, 1).value
            order_no = sheet.cell(row, 0).value
            due_date = sheet.cell(row, 2).value
            sku = sheet.cell(row, 3).value
            buyerupcode = sheet.cell(row, 6).value
            qty = sheet.cell(row, 4).value
            rate = sheet.cell(row, 5).value
            buyer_order_no = sheet.cell(row, 8).value
            brand = sheet.cell(row, 9).value
            partner_id = self.env['res.partner'].search([
                ('name', '=', customer_name),
            ], limit=1)
            if not partner_id:
                raise UserError(_('Buyer not found'))
            order_id = self.env['inno.sale.order.planning'].search([
                ('order_no', '=', order_no),
            ], limit=1)
            if not order_id or order_id and order_id.state == 'draft':
                product_id = self.env['product.product'].search([
                    ('default_code', '=', sku),
                ], limit=1)
                if not product_id:
                    product_id = self.env['inno.sku.product.mapper'].search([('sku', '=', sku)]).product_id
                if not product_id:
                    sku_not_found.append(sku)
                    continue
                elif sku in skus_added:
                    raise UserError(_(f'Duplicate SKU {sku} found'))
                else:
                    skus_added.append(sku)
                if not order_id:
                    order_id = self.env['inno.sale.order.planning'].create({
                        'customer_name': partner_id.id,
                        'order_date': xlrd.xldate_as_datetime(order_date, 0).date(),
                        'due_date': xlrd.xldate_as_datetime(due_date, 0).date(),
                        'order_no': order_no,
                        'buyer_order_no': buyer_order_no,
                        'state': 'draft',
                        'assigned_to': self.env.user.id
                    })
                if order_id:
                    planning_line = self.env['inno.sale.order.planning.line'].create({
                        'product_id': product_id.id,
                        'product_uom_qty': float(qty),
                        'rate': float(rate),
                        'buyer_up_code': buyerupcode,
                        'brand': brand,
                        'sale_order_planning_id': order_id.id,
                        'remaining_qty': float(qty)
                    })
                    if planning_line:
                        order_id.sale_order_planning_lines += planning_line
                if order_id.id not in records:
                    records.append(order_id.id)
        if sku_not_found:
            raise UserError(_(f"SKU's not found\n {', '.join(sku_not_found)}"))

        self.env['inno.sale.order.planning'].browse(records).write({'state': 'planning'})

        if len(records) < 1:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': _("No records imported.\nRecord already available for the given order number."),
                    'next': {'type': 'ir.actions.act_window_close'},
                }
            }

        action = {
            'name': _("Sale Plannings"),
            'view_mode': 'form',
            'res_model': 'inno.sale.order.planning',
            'type': 'ir.actions.act_window',
        }
        if len(records) > 1:
            print(records)
            print('multi')
            action.update({'view_mode': 'tree,form', 'domain': [('id', '=', records)]})
        else:
            print('one')
            action.update({'view_type': 'form', 'res_id': records[0]})
        return action