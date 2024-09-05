import math

import reportlab.graphics.barcode.code128

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests
import json
from dateutil import parser
import logging
import base64

_logger = logging.getLogger(__name__)


class MigrationRecord(models.Model):
    _name = 'inno.migration.record'
    _description = 'Migration Record'

    name = fields.Char(string='Reference')
    data = fields.Text(string='Data')
    operation_type = fields.Selection(selection=[('pending_sale', 'Pending Sale Order'),
                                                 ('weaving_order', 'Weaving Order'), ('finishing', 'Finishing'),
                                                 ('finishing_bazaar', 'Finishing Bazaar'),
                                                 ('weaving_baazar', 'Weaving Baazar'),
                                                 ('account', 'Account'), ('stock', 'Stock'), ('carpet', 'Carpet'),
                                                 ('per_day_invoice', 'Invoice Per Day'), ('to_be_issue', 'To Be Issue'),
                                                 ('on_loom_material', 'Material On Loom')])
    finishing_operation_id = fields.Many2one(comodel_name='mrp.workcenter')
    state = fields.Selection(selection=[('draft', 'Draft'), ('partial', 'Partial'), ('completed', 'Completed')],
                             default='draft')
    logs_ids = fields.One2many(comodel_name='inno.migration.logs', inverse_name='migration_id')
    partner_id = fields.Many2one(comodel_name='res.partner', string='Customer')
    division = fields.Char()
    job_work = fields.Many2one("main.jobwork", string="Job Work")
    purchase_job_work = fields.Many2one("inno.purchase", string="Purchase Job Work")
    location = fields.Char()
    current_order = fields.Boolean(string="Is Current Order?")
    warehouse = fields.Char()
    product_type = fields.Char()
    site = fields.Char()
    product_group = fields.Char()

    def update_picking_report(self, picking_id):
        rec = self.env['stock.picking'].browse(picking_id)
        if not rec:
            raise UserError(_("No picking found"))
        pdf = self.env.ref('innorug_manufacture.action_report_material_gate_pass',
                           raise_if_not_found=False).sudo()._render_qweb_pdf('innorug_manufacture.'
                                                                             'action_report_material_gate_pass',
                                                                             res_ids=rec.id)[0]
        pdf = base64.b64encode(pdf).decode()
        attachment = self.env['ir.attachment'].create({'name': f"Gate Pass: {self.name}",
                                                       'type': 'binary',
                                                       'datas': pdf,
                                                       'res_model': 'stock.picking',
                                                       'res_id': rec.id,
                                                       })
        rec.message_post(body="Gate Pass Generated", attachment_ids=[attachment.id])

    def get_to_be_issue(self):
        apis = {'tufted': 'http://103.70.145.253:125/api/TobeIssuesOrder/GetTobeIssueOrderMainTufted',
                'knotted': 'http://103.70.145.253:125/api/TobeIssuesOrder/GetTobeIssueOrderMainKnotted',
                'kelim': 'http://103.70.145.253:125/api/TobeIssuesOrder/GetTobeIssueOrderMainKelim',
                'chaksari': 'http://103.70.145.253:125/api/TobeIssuesOrder/GetTobeIssueOrderChaksariTufted',
                'fattupur': 'http://103.70.145.253:125/api/TobeIssuesOrder/GetTobeIssueOrderFattupurTufted',
                'sarwatkhani': 'http://103.70.145.253:125/api/TobeIssuesOrder/GetTobeIssueOrderSarwatkhaniTufted'}
        try:
            response = requests.get(url=apis.get(self._context.get('type')))
            if response.status_code == 200:
                vals = [{'name': self.env['ir.sequence'].next_by_code('inno.migration.record'), 'data': data,
                         'operation_type': 'to_be_issue'} for data in json.loads(response.text)]
                if vals:
                    self.create(vals)
                    self._cr.commit()
            else:
                raise UserError(_(response.reason))
        except Exception as ex:
            raise UserError(ex)

    def process_to_be_issue(self):
        for rec in self.search([('operation_type', '=', 'to_be_issue'), ('state', 'in', ['draft', 'partial'])]):
            data = json.loads(
                rec.data.replace("'", '"').replace('""', '"').replace('"X', '').replace('" ', '').replace('"OV',
                                                                                                          '').replace(
                    '"HM', '').replace('"SH"', '"').replace('"KD', '').replace('"SH R"', '"'))
            sale_order = self.env['sale.order'].search([('order_no', '=', data.get('docNo').replace(' ', ''))], limit=1)
            product_id = self.env['product.product'].search([('default_code', '=', data.get('productName'))], limit=1)
            if not product_id:
                product_id = self.env['inno.sku.product.mapper'].search([
                    ('sku', '=', data.get('productName'))], limit=1).product_id
            if not product_id:
                self.create_product_through_api(data.get('productName'))
                self._cr.commit()
            product_id = self.env['product.product'].search([('default_code', '=', data.get('productName'))], limit=1)
            if not product_id:
                rec.write({'logs_ids': [(0, 0, {'error_description': 'Product Not Found in the system',
                                                'name': 'Product not found'})], 'state': 'partial'})
                continue
            bom = self.env['mrp.bom'].search([('product_id', '=', product_id.id)])
            if bom:
                self.sync_bom_operations(bom)
            else:
                rec.write({'logs_ids': [(0, 0, {'error_description': 'Bom Not Found in the system',
                                                'name': 'Bom not found'})], 'state': 'partial'})
                continue
            if sale_order and sale_order.state == 'draft' and product_id:
                tax_id = False
                if sale_order.partner_id.id == 675:
                    if product_id.product_tmpl_id.face_content.name in ['100% Polyester', '100% Polyster']:
                        tax_id = [4, 76]
                    else:
                        tax_id = [4, 77]
                line = sale_order.order_line.filtered(lambda ol: ol.product_id.id == product_id.id)
                if line:
                    line.product_uom_qty = line.product_uom_qty + data.get('balanceQty')
                    rec.state = 'completed'
                else:
                    sale_order.write({'order_line': [(0, 0,
                                                      {'product_id': product_id.id, 'to_be_issue': True,
                                                       'price_unit': 0.0, 'tax_id': tax_id,
                                                       'pending_sale_order_qty': data.get('pendingSaleOrderQty'),
                                                       'Total_sale_qty': data.get('saleOrderQty'),
                                                       'product_uom_qty': data.get('balanceQty')})]})
                    rec.state = 'completed'
            if not sale_order:
                buyer = self.env['res.partner'].search([('name', '=', data.get('buyerName'))])
                if not buyer:
                    rec.write({'logs_ids': [(0, 0, {'error_description': 'Buyer Not Found in the system',
                                                    'name': 'Buyer not found'})], 'state': 'partial'})
                    continue
                tax_id = False
                if buyer.id == 675:
                    if product_id.product_tmpl_id.face_content.name in ['100% Polyester', '100% Polyster']:
                        tax_id = [4, 76]
                    else:
                        tax_id = [4, 77]
                order_line = [(0, 0, {'product_id': product_id.id, 'to_be_issue': True,
                                      'pending_sale_order_qty': data.get('pendingSaleOrderQty'),
                                      'Total_sale_qty': data.get('saleOrderQty'), 'tax_id': tax_id,
                                      'product_uom_qty': data.get('balanceQty'),
                                      'price_unit': 0.0})]
                sale_order = self.env['sale.order'].create({'partner_id': buyer.id,
                                                            'order_no': data.get('docNo'),
                                                            'order_line': order_line,
                                                            'pricelist_id': 2})
                sale_order.write({'date_order': parser.parse(data.get('date')),
                                  'expected_date': parser.parse(data.get('dueDate'))})
                rec.state = 'completed'
            self._cr.commit()

    def trim_orders_down(self):
        for rec in self.env['sale.order.line'].search([]):
            rec.product_uom_qty = math.floor(rec.product_uom_qty)

    def get_carpet_stock(self):
        for division in self.env['mrp.division'].search([]):
            try:
                if self.search([('division', '=', division.name), ('operation_type', '=', 'carpet')]):
                    continue
                response = requests.get(
                    url=f'http://103.70.145.253:125/api/InventoryData/GetCarpetInventoryData?devision={division.name}')
                if response.status_code == 200:
                    vals = [{'name': self.env['ir.sequence'].next_by_code('inno.migration.record'), 'data': data,
                             'division': division.name, 'operation_type': 'carpet'} for data in
                            json.loads(response.text)]
                    if vals:
                        self.create(vals)
                        self._cr.commit()
                else:
                    raise UserError(_(response.reason))
            except Exception as ex:
                raise UserError(ex)

    def process_carpet_stock(self):
        for rec in self.search([('state', 'in', ['draft', 'partial']), ('operation_type', '=', 'carpet')]):
            data = json.loads(rec.data.replace("'", '"'))
            location_id = self.env['stock.location'].search([
                ('complete_name', '=', f'{data.get("godownName")}/Stock')], limit=1)
            if not location_id:
                rec.write({'logs_ids': [(0, 0, {'error_description': 'location not found in the system',
                                                'name': 'location not found'})], 'state': 'draft'})
                continue
            product_id = self.env['product.product'].search([('default_code', '=', data.get('productName'))])
            if not product_id:
                rec.write({'logs_ids': [(0, 0, {'error_description': 'Product not found in the system',
                                                'name': 'Product not found'})], 'state': 'draft'})
                continue
            stock_record = self.env['inno.stock.migration'].search(
                [('product_id', '=', product_id.id), ('location_id', '=', location_id.id)])
            if stock_record:
                rec.state = 'completed'
                continue
            self.env['inno.stock.migration'].create({'product_id': product_id.id, 'location_id': location_id.id,
                                                     'opening': data.get('opening')})
            self._cr.commit()

    def get_invoice_per_day(self):
        try:
            response = requests.get(url='http://103.70.145.253:125/api/InventoryData/GetInvoicePerDay')
            if response.status_code == 200:
                vals = [{'name': self.env['ir.sequence'].next_by_code('inno.migration.record'), 'data': data,
                         'operation_type': 'per_day_invoice'} for data in json.loads(response.text)]
                if vals:
                    self.create(vals)
                    self._cr.commit()
            else:
                raise UserError(_(response.reason))
        except Exception as ex:
            _logger.error(f"============================================================ Fetching Invoice per day{ex}")
            raise UserError(ex)

    def process_invoice_per_day(self):
        weaving_journal_id = self.env['inno.config'].sudo().search([], limit=1).weaving_journal_id
        finishing_journal_id = self.env['inno.config'].sudo().search([], limit=1).finishing_journal_id
        invoice = []
        for rec in self.search([('state', 'in', ['draft', 'partial']), ('operation_type', '=', 'per_day_invoice')]):
            data = json.loads(rec.data.replace("'", '"'))
            journal_id = weaving_journal_id if data.get("processName") == 'Weaving' else finishing_journal_id
            partner_id = self.env['res.partner'].search([('name', '=', data.get('name'))], limit=1)
            if not partner_id:
                rec.write({'logs_ids': [(0, 0, {'error_description': 'Partner not found in the system',
                                                'name': 'Partner not found'})], 'state': 'draft'})
                continue
            product_id = self.env['product.product'].search([('default_code', '=', data.get('productName'))], limit=1)
            if not product_id:
                rec.write({'logs_ids': [(0, 0, {'error_description': 'Product not found in the system',
                                                'name': 'Product not found'})], 'state': 'draft'})
                continue
            bill = self.env['account.move'].search([('ref', '=', data.get('docNo'))], limit=1)
            invoice_line = [(0, 0, {'product_id': product_id.id, 'quantity': 1, 'price_unit': data.get('amount'),
                                    'tax_ids': False, 'account_id': journal_id.default_account_id.id})]
            if bill and bill.state == 'draft':
                bill.write({'invoice_line_ids': invoice_line})
                if bill.id not in [rec.id for rec in invoice]:
                    invoice.append(bill)
            else:
                bill = self.env['account.move'].create({
                    'ref': data.get('docNo'),
                    'move_type': 'in_invoice',
                    'partner_id': partner_id.id,
                    'date': parser.parse(data.get('docDate')),
                    'invoice_date': fields.Datetime.now(),
                    'invoice_line_ids': invoice_line,
                    'journal_id': journal_id.id
                })
                invoice.append(bill)
            rec.state = 'completed'
        self._cr.commit()
        for rec in invoice:
            rec.action_post()
            self.env['account.payment.register'].with_context(active_model='account.move',
                                                              active_ids=rec.id).create({
                'amount': rec.amount_total
            })._create_payments()
            # wizard = Form(self.env['account.payment.register'].with_context(action_data['context'])).save()
            # action = wizard.action_create_payments()

    def get_opening_stock(self):
        rec = f"Site={self.site}&Division={self.division}&&Godown={self.warehouse}"
        if self.product_type:
            rec += f'&productType={self.product_type}'
        elif self.product_group:
            rec += f'&productType={self.product_group}'
        try:
            response = requests.get(
                url=f'http://103.70.145.253:125/api/InventoryData/GetInventoryData?{rec}')
            if response.status_code == 200:
                vals = [{'name': self.env['ir.sequence'].next_by_code('inno.migration.record'), 'data': data,
                         'warehouse': self.warehouse, 'product_type': self.product_type,
                         'operation_type': 'stock'} for data in json.loads(response.text)]
                if vals:
                    self.create(vals)
                    self._cr.commit()
            else:
                raise UserError(_(response.reason))
        except Exception as ex:
            raise UserError(ex)

    def get_material_on_loom(self):
        records = {'Tufted': ['Main', 'Fattupur', 'Chaksari', 'Sarvatkhani'], 'Kelim': ['Main'], 'Knotted': ['Main']}
        try:
            for division, sites in records.items():
                for site in sites:
                    if self.search_count([('operation_type', '=', 'on_loom_material'), ('division', '=', division),
                                          ('site', '=', site)]) == 0:
                        response = requests.get(
                            url=f'http://103.70.145.253:125/api/InventoryData/GetMaterialOnLoom?site={site}&division={division}')
                        if response.status_code == 200:
                            vals = [
                                {'name': self.env['ir.sequence'].next_by_code('inno.migration.record'), 'data': data,
                                 'division': division, 'site': site,
                                 'operation_type': 'on_loom_material'} for data in json.loads(response.text)]
                            if vals:
                                self.create(vals)
                                self._cr.commit()
        except Exception as ex:
            _logger.info(f"========================================================={ex}")

    def process_material_on_loom(self):
        for rec in self.search([('operation_type', '=', 'on_loom_material'), ('state', 'in', ['draft', 'partial'])]):
            try:
                data = json.loads(rec.data.replace("'", '"').replace('None', '"n/a"'))
            except Exception as ex:
                rec.write({'logs_ids': [(0, 0, {'error_description': 'Json Error',
                                                'name': 'Process Manually'})], 'state': 'partial'})
                self._cr.commit()
                continue
            division = 6 if rec.division == 'Tufted' else 2 if rec.division == 'Knotted' else 1 if rec.division == 'Kelim' else False
            if not division:
                rec.write({'logs_ids': [(0, 0, {'error_description': 'Division not found in the system',
                                                'name': 'Division not found'})], 'state': 'partial'})
                self._cr.commit()
                continue
            if division == 2 and rec.site != 'Main':
                branch = 14 if rec.site == 'Chaksari' else 15 if rec.site == 'Sarvatkhani' else 25 if rec.site == 'Fattupur' else False
                if branch:
                    weaving_order = self.env['main.jobwork'].search(
                        [('parallel_order_number', '=', data.get('docNo')), ('division_id', '=', division),
                         ('branch_id', '=', branch)], limit=1)
                else:
                    weaving_order = False
            else:
                weaving_order = self.env['main.jobwork'].search(
                    [('parallel_order_number', '=', data.get('docNo')), ('division_id', '=', division)], limit=1)
            if not weaving_order:
                rec.write(
                    {'logs_ids': [(0, 0, {'error_description': f'Weaving order not found in the system: {rec.division}',
                                          'name': 'Weaving not found'})], 'state': 'partial'})
                self._cr.commit()
                continue
            design = self.env['product.template'].search([('name', '=', data.get("productGroupName"))], limit=1)
            if not design:
                rec.write({'logs_ids': [
                    (0, 0, {'error_description': f'Design not found in the system: {rec.division}',
                            'name': 'design not found'})], 'state': 'partial'})
                self._cr.commit()
                continue
            product_id = False
            if data.get('dimension1Name') in [None, '', False, 'n/a'] and design.product_variant_ids.__len__() == 1:
                product_id = design.product_variant_ids
            else:
                product_id = design.product_variant_ids.filtered(
                    lambda pv: pv.product_template_attribute_value_ids.product_attribute_value_id.name == data.get(
                        'dimension1Name'))
                if not product_id:
                    product_id = design.product_variant_ids.filtered(
                        lambda
                            pv: pv.product_template_attribute_value_ids.product_attribute_value_id.name == data.get(
                            'dimension1Name').strip())
            if not product_id:
                rec.write({'logs_ids': [
                    (0, 0, {'error_description': f'Product not found in the system: {rec.division}',
                            'name': 'Product not found'})], 'state': 'partial'})
                self._cr.commit()
                continue
            stock_line = weaving_order.alloted_material_ids.filtered(lambda al: al.product_id.id == product_id.id)
            if not stock_line:
                rec.write({'logs_ids': [
                    (0, 0, {'error_description': f'Stock Line not found in the system: {rec.division}',
                            'name': 'Material not found'})], 'state': 'partial'})
                self._cr.commit()
                continue
            stock_line.write({'quantity_released': stock_line.alloted_quantity + data.get('balanceOnLoom'),
                              'old_balance': data.get('balanceOnLoom')})
            rec.state = 'completed'
            self._cr.commit()

    def process_opening_stock(self):
        shade_attrib = self.env['product.attribute'].search([('name', '=', 'SHADE')])
        for rec in self.search([('state', 'in', ['draft', 'partial']), ('operation_type', '=', 'stock')]):
            try:
                data = json.loads(rec.data.replace("'", '"'))
            except Exception as ex:
                continue
            warehouse = self.env['stock.warehouse'].search([('name', '=', data.get("godownName"))], limit=1)
            location_id = self.env['stock.location'].search([
                ('complete_name', '=', f'{warehouse.code}/Stock')], limit=1)
            if not location_id:
                rec.write({'logs_ids': [(0, 0, {'error_description': 'location not found in the system',
                                                'name': 'location not found'})], 'state': 'partial'})
                continue
            product_id = self.env['product.product'].search([('default_code', '=', data.get('productName'))], limit=1)
            if not product_id:
                design = self.env['product.template'].search([('name', '=', data.get('productName').strip())], limit=1)
                if not design:
                    attribute_id = self.env['product.attribute'].search([('name', '=', 'SHADE')], limit=1)
                    if data.get('dimension1Name') == '':
                        atttrs_value = 'NO Shade'
                    else:
                        atttrs_value = data.get('dimension1Name').upper()
                    attribute_value = self.env['product.attribute.value'].search([
                        ('attribute_id', '=', attribute_id.id),
                        ('name', '=', atttrs_value.strip())], limit=1)
                    if not attribute_value:
                        attribute_value = self.env['product.attribute.value'].create({
                            'name': atttrs_value.strip(),
                            'attribute_id': attribute_id.id,
                        })
                    uom_dict = {'MET': 'm', 'MT2': 'm²', 'YD2': 'Sq. Yard', 'KG': 'kg', 'PCS': 'Units',
                                'Sq.Meter': 'm²', 'METER': 'm'}
                    uom_id = self.env['uom.uom'].search([('name', '=', uom_dict.get(data.get('unitName')))], limit=1)
                    if uom_id:
                        materials = {'name': data.get('Product'), 'uom_id': uom_id.id, 'uom_po_id': uom_id.id,
                                     'sale_ok': True, 'purchase_ok': True, 'is_raw_material': True,
                                     'detailed_type': 'product', 'invoice_policy': 'delivery',
                                     'raw_material_group': self.raw_material_group
                                     }
                        design = self.env['product.template'].create(materials)
                        shade = self.env['product.attribute.value'].search([('id', '=', attribute_value)], limit=1)
                        if attribute_value:
                            design.attribute_line_ids.filtered(lambda al: al.attribute_id.id == attribute_id.id).write(
                                {'value_ids': [(4, attribute_value)]})
                            if not design.attribute_line_ids:
                                self.create_attrribute_in_matrial(design, attribute_id, attribute_value)
                if not design:
                    rec.write({'logs_ids': [(0, 0, {'error_description': 'Design not found in the system',
                                                    'name': 'Design not found'})], 'state': 'partial'})
                    continue
                shade = 'NO Shade' if data.get('dimension1Name') == '' else data.get('dimension1Name').strip()
                product_id = design.product_variant_ids.filtered(
                    lambda pv: pv.product_template_attribute_value_ids.product_attribute_value_id.name == shade)
                if not product_id and design.product_variant_ids.__len__() == 1:
                    product_id = design.product_variant_ids
                if not product_id:
                    try:
                        attribute_value_id = self.env['product.attribute.value'].search([
                            ('attribute_id', '=', shade_attrib.id), ('name', '=', shade)], limit=1)
                        if not attribute_value_id:
                            attribute_value_id = self.env['product.attribute.value'].create({
                                'name': shade,
                                'attribute_id': shade_attrib.id,
                            })
                        design.attribute_line_ids.write({'value_ids': [(4, attribute_value_id.id)]})
                        product_id = design.product_variant_ids.filtered(
                            lambda pv: pv.product_template_attribute_value_ids.product_attribute_value_id.name == shade)
                        self._cr.commit()
                    except:
                        pass
                if not product_id:
                    rec.write({'logs_ids': [(0, 0, {'error_description': 'Product not found in the system',
                                                    'name': 'Product not found'})], 'state': 'partial'})
                    continue
            stock_record = self.env['inno.stock.migration'].search(
                [('product_id', '=', product_id.id), ('location_id', '=', location_id.id)])
            if stock_record:
                rec.state = 'completed'
                self._cr.commit()
                continue
            self.env['inno.stock.migration'].create({'product_id': product_id.id, 'location_id': location_id.id,
                                                     'opening': data.get('opening'), 'balance': data.get('balQty')})
            rec.state = 'completed'
            self._cr.commit()

    def create_attrribute_in_matrial(self, design, attribute_id, attribute_value):
        if attribute_value:
            design.update({
                'attribute_line_ids': [
                    (0, 0, {'attribute_id': attribute_id.id,
                            'value_ids': [
                                (4, attribute_value)]})]})

    def update_barcode_data(self, main_jobwork_id, lines, work_order_id, data, branch_id, bfield):
        bcodes = self.env['mrp.barcode'].search([('mrp_id', '=', work_order_id.production_id.id),
                                                 ('state', '=', '1_draft'), ('old_system_barcode', '=', False)])
        if bcodes:
            bcodes = bcodes[0]
            bcodes.write({'state': '3_allocated', f'{bfield}': False if branch_id else main_jobwork_id.id,
                          'branch_main_job_work_id': main_jobwork_id if branch_id else False,
                          'current_process': work_order_id.id, 'old_system_barcode': data.get('productUidName'),
                          'branch_id': branch_id.id if branch_id else False,
                          'next_process': self.env['mrp.workorder'].search([('parent_id', '=', work_order_id.id)]).id})
        _logger.info("........ update_barcode_data - %r ........", bcodes)
        return bcodes

    def check_barcode_data(self, main_jobwork_id, lines, work_order_id, data, branch_id, bfield):
        bcodes = self.env['mrp.barcode'].search([('mrp_id', '=', work_order_id.production_id.id),
                                                 ('state', '=', '3_allocated'),
                                                 ('old_system_barcode', '=', data.get('productUidName'))])[0]
        _logger.info("........ check_barcode_date - %r ........", bcodes)
        if bcodes:
            main_jobwork_id.write(
                {'parent_job_work_id': bcodes.main_job_work_id.id, 'barcode_released': True, 'branch_id': branch_id.id})
            bcodes.write({'state': '3_allocated', f'{bfield}': main_jobwork_id.id})
            return bcodes
        return False

    def check_main_job_work(self, partner_id, division, work_order_id, data, job_work, div, rec, product_id):
        main_jobworks = self.env[job_work].search(
            [('subcontractor_id', '=', partner_id.id), ('division_id', '=', division.id),
             ('parallel_order_number', '=', data.get('docNo'))])
        # if rec.division == 'Handloom Tufted' and main_jobworks:
        #      return main_jobworks, division
        if main_jobworks:
            return main_jobworks, division
        else:
            if div.get(rec.division).upper() in ['FATTUPUR', 'CHAKSARI', 'SARVATKHANI']:
                division = self.env['mrp.division'].search([('name', '=', 'TUFTED')])
                main_jobworks = self.env[job_work].search(
                    [('subcontractor_id', '=', partner_id.id), ('division_id', '=', division.id)])
                if main_jobworks:
                    main = main_jobworks.filtered(
                        lambda jl: work_order_id.id in jl.jobwork_line_ids.mrp_work_order_id.ids)
                    if main.parallel_order_number == data.get('docNo'):
                        main_jobwork_id = main
                        return main_jobwork_id, division
                    else:
                        if main:
                            main_jobwork_id = main.write({"parallel_order_number": data.get('docNo')})
                            return main_jobwork_id, division
                else:
                    return False, division
            else:
                return False, division

    def check_product_with_po_and_create(self, main_jobwork_id, work_order_id, rec, data, product_id, branch_id, bfield,
                                         job_work):
        job_work_lines = main_jobwork_id.jobwork_line_ids.filtered(
            lambda jl: jl.product_id.id == product_id.id and jl.sale_order_number == data.get('saleOrderNo'))
        if job_work_lines:
            job_work_lines.product_qty += 1
            if work_order_id:
                job_work_lines.write({'mrp_work_order_id': work_order_id.id})
                bcodes = self.update_barcode_data(main_jobwork_id, job_work_lines, work_order_id, data, branch_id,
                                                  bfield)
                work_order_id._compute_allotment_status()
                job_work_lines.write({'barcodes': [(4, bcodes.id)]})
            _logger.info("........ check_product_with_po_and_create- %r ........")
            job_work_lines.write({'total_area': job_work_lines.area * job_work_lines.product_qty, })
            rec.write({'state': 'completed', f'{job_work}': main_jobwork_id.id})
        else:
            main_jobwork_id.write({'jobwork_line_ids': [(0, 0, {
                "mrp_work_order_id": work_order_id.id, 'issue_date': data.get('docDate'),
                "product_qty": 1, "product_id": product_id.id,
                "area": product_id.mrp_area,
                "sale_order_number": data.get('saleOrderNo'),
                'uom_id': product_id.sudo().get_rate_list_uom(work_order_id.workcenter_id),
                "total_area": product_id.mrp_area,
                'original_rate': data.get('rate'),
            })]})
            job_work_lines = main_jobwork_id.jobwork_line_ids.filtered(
                lambda jl: jl.product_id.id == product_id.id and jl.sale_order_number == data.get('saleOrderNo'))
            if work_order_id:
                if rec.division in ['Fattupur Tufted', 'Chaksari Tufted', 'Sarwatkhani Tufted']:
                    bcodes = self.check_barcode_data(main_jobwork_id, job_work_lines, work_order_id, data,
                                                     branch_id, bfield)
                    job_work_lines.write({'barcodes': [(4, bcodes.id)]})
                else:
                    bcodes = self.update_barcode_data(main_jobwork_id, job_work_lines, work_order_id, data,
                                                      branch_id, bfield)
                    job_work_lines.write({'barcodes': [(4, bcodes.id)]})
                work_order_id._compute_allotment_status()
            job_work_lines.write({
                'total_area': job_work_lines.area * job_work_lines.product_qty,
            })
            rec.write({'state': 'completed', f'{job_work}': main_jobwork_id.id})

    def process_weaving_sale_order(self):
        product = self.env['product.product'].search([('inno_mrp_size_id', '!=', False)])
        for line in product:
            line.default_code = line.default_code.strip()
        for line in self.env['sale.order'].search([]):
            line.order_no = line.order_no.strip()
        self._cr.commit()
        for rec in self.search([('state', '=', 'draft'), ('operation_type', '=', 'weaving_order')]):
            try:
                new = rec.data.replace('None', '4')
                data = json.loads(new.replace("'", '"'))
                division = {'knotted': 'KNOTTED', 'kelim': 'KELIM',
                            'tufted': 'TUFTED', 'Fattupur Tufted': 'W.C.FATTUPUR', 'Handloom Tufted': 'TUFTED',
                            'Chaksari Tufted': 'W.C.CHAKSARI',
                            'W.C.FATTUPUR': 'W.C.FATTUPUR', 'W.C.CHAKSARI': 'W.C.CHAKSARI',
                            'W.C.SARVATKHANI': 'W.C.SARVATKHANI',
                            'Sarwatkhani Tufted': 'W.C.SARVATKHANI',
                            'Main Tufted Finishing Weaving': 'Tufted Purchase',
                            'Main kelim Finishing Weaving': 'Kelim Purchase',
                            'branch tufted': 'BRANCH TUFTED'}
                partner_id = self.env['res.partner'].search([('name', '=', data.get('name'))], limit=1)
                if not partner_id:
                    partner_id = self.env['res.partner'].create({
                        'name': data.get('name')})
                sale_order = self.env['sale.order'].search([('order_no', '=', data.get('saleOrderNo').strip())],
                                                           limit=1)
                pl = []
                for sb in self.env['sale.order'].search([]):
                    pl.append(sb.order_no)
                if not sale_order:
                    rec.write({'logs_ids': [(0, 0, {'error_description': 'Sale Order not found ',
                                                    'name': data.get('name')})], 'state': 'partial'})
                    continue
                product_id = self.env['product.product'].search(
                    [('default_code', '=', data.get('productName').strip())])
                if not product_id:
                    rec.write({'logs_ids': [(0, 0, {'error_description': 'Product Not Found ',
                                                    'name': data.get('name')})], 'state': 'partial'})
                    continue
                work_order_id = sale_order.mrp_production_ids.filtered(
                    lambda wo: wo.product_id.id == product_id.id).workorder_ids.filtered(
                    lambda wo: wo.name == 'Weaving')
                if not work_order_id:
                    rec.write({'logs_ids': [(0, 0, {'error_description': 'Work order not found ',
                                                    'name': data.get('name')})], 'state': 'partial'})
                    continue
                bcodes = self.env['mrp.barcode'].search(
                    [('old_system_barcode', '=', data.get('productUidName'))]) if sale_order else False
                if bcodes:
                    rec.write({'logs_ids': [(0, 0, {'error_description': 'Barcode already Mapped ',
                                                    'name': data.get('name')})], 'state': 'partial'})
                    continue
                if not bcodes and product_id and work_order_id:
                    division_id = self.env['mrp.division'].search([('name', '=', division.get(rec.division).upper())]) \
                        if self.env['mrp.division'].search([('name', '=', division.get(rec.division).upper())]) \
                        else self.env['mrp.division'].search([('name', '=', 'TUFTED')])
                    branch_id = self.env['weaving.branch'].search([('name', '=', division.get(data.get('name')).upper()
                    if rec.division == 'branch tufted' else division.get(rec.division).upper())]) \
                        if rec.division in ['branch tufted', 'Fattupur Tufted', 'Chaksari Tufted', 'Sarwatkhani Tufted'] \
                        else False
                    if rec.division in ['knotted', 'kelim', 'tufted', 'branch tufted', 'Handloom Tufted',
                                        'Fattupur Tufted', 'Chaksari Tufted', 'Sarwatkhani Tufted']:
                        if division_id or branch_id:
                            job_work = 'main.jobwork'
                            main_jobwork_id, division_id = rec.check_main_job_work(partner_id, division_id,
                                                                                   work_order_id, data, job_work,
                                                                                   division, rec, product_id)
                            _logger.info("........ main job work - %r ........", main_jobwork_id)
                            config = self.env['inno.config'].sudo().search([], limit=1)
                            if not main_jobwork_id:
                                main_jobwork_id = self.env['main.jobwork'].create({
                                    'issue_date': data.get('docDate'),
                                    'expected_received_date': data.get('dueDate'),
                                    'loss': data.get('lossQty'),
                                    'division_id': division_id.id,
                                    'parallel_order_number': data.get('docNo'),
                                    'subcontractor_id': branch_id.partner_id.id if branch_id else partner_id.id,
                                    'is_branch_subcontracting': True if branch_id else False,
                                    'weaving_center_name': branch_id.name if branch_id else False,
                                    'operation_id': work_order_id.workcenter_id.id,
                                    'reference': self.env['ir.sequence'].next_by_code('weaving.center.job.work')
                                    if rec.division in ['Fattupur Tufted', 'Chaksari Tufted', 'Sarwatkhani Tufted']
                                    else self.env['ir.sequence'].next_by_code('main.jobwork'),
                                    'allowed_chunks': config.allowed_fragments,
                                })
                            else:
                                main_jobwork_id.write(
                                    {'parallel_order_number': data.get('docNo'), 'loss': data.get('lossQty'),
                                     'issue_date': data.get('docDate'),
                                     'expected_received_date': data.get('dueDate'), })
                            if main_jobwork_id:
                                rec.check_product_with_po_and_create(main_jobwork_id, work_order_id, rec, data,
                                                                     product_id, branch_id, 'main_job_work_id',
                                                                     'job_work')

                    elif rec.division in ['Main Tufted Finishing Weaving', 'Main kelim Finishing Weaving']:
                        branch_id = False
                        job_work = 'main.jobwork'
                        main_jobwork_id, division_id = rec.check_main_job_work(partner_id, division_id, work_order_id,
                                                                               data, job_work, division, rec,
                                                                               product_id)
                        if not main_jobwork_id:
                            main_jobwork_id = self.env[job_work].create({
                                'issue_date': data.get('docDate'),
                                'expected_received_date': data.get('dueDate'),
                                'loss': data.get('lossQty'),
                                'division_id': division_id.id,
                                'parallel_order_number': data.get('docNo'),
                                'subcontractor_id': partner_id.id,
                                'is_branch_subcontracting': True if branch_id else False,
                                'operation_id': work_order_id.workcenter_id.id,
                                'is_full_finish': True,
                                'reference': self.env['ir.sequence'].next_by_code('main.jobwork'),
                            })
                        else:
                            main_jobwork_id.write(
                                {'parallel_order_number': data.get('docNo'), 'loss': data.get('lossQty'),
                                 'issue_date': data.get('docDate'),
                                 'expected_received_date': data.get('dueDate'), })
                        if main_jobwork_id:
                            rec.check_product_with_po_and_create(main_jobwork_id, work_order_id, rec, data, product_id,
                                                                 branch_id, 'main_job_work_id', 'job_work')
            except Exception as ex:
                rec.write({'logs_ids': [(0, 0, {'error_description': ex, })], 'state': 'partial'})
            _logger.info("........ final job work - %r ........", )
            self._cr.commit()

    def create_product_through_api(self, sku):
        host = f'http://103.70.145.253:125/api/ProductMgt/GetProductBySKU?SKU={sku}'
        try:
            response = requests.get(url=host)
            product_id = False
            if response.status_code == 200:
                for data in json.loads(response.text):
                    product_id = self.env['product.product'].search([('default_code', '=', sku)],
                                                                    limit=1)
                    boms = False
                    if not product_id:
                        product_id = self.create_product_templ_record(data)
                        boms = product_id.product_tmpl_id.bom_ids
                        if boms:
                            boms = boms.filtered(lambda bm: not bm.product_id)
                            new_bom = boms.copy()
                            new_bom.write({'product_id': product_id.id})
                            self.re_sync_materials(boms, product_id)
                            self.re_sync_operations(boms, product_id)
                    if product_id and not boms:
                        self.create_bom_and_operation(product_id)
                        boms = product_id.product_tmpl_id.bom_ids.filtered(lambda bm: not bm.product_id)
                        new_bom = boms.copy()
                        new_bom.write({'product_id': product_id.id})
                        self.re_sync_materials(boms, product_id)
                        self.re_sync_operations(boms, product_id)
                return product_id
            else:
                raise UserError(_(response.reason))
        except Exception as ex:
            raise UserError(ex)

    def create_bom_and_operation(self, product_id):
        host = f'http://103.70.145.253:125/api/ProductMgt/GetProductSequence?Design={product_id.product_tmpl_id.name}'
        try:
            response = requests.get(url=host)
            if response.status_code == 200:
                for data in json.loads(response.text):
                    work_center_id = self.env['mrp.workcenter'].search([('name', '=', data.get('processName')), ],
                                                                       limit=1)
                    if not product_id.product_tmpl_id.bom_ids:
                        product_id.product_tmpl_id.write(
                            {'bom_ids': self.create_bom_design_bom(product_id.product_tmpl_id, data.get('processName'),
                                                                   data.get('sr'), work_center_id)})
                    else:
                        product_id.product_tmpl_id.bom_ids[0].write({'operation_ids': self.create_bom_varient_operation(
                            data.get('processName'), data.get('sr'), work_center_id)})
                if response.text:
                    return self.create_api_with_bom(product_id)
            else:
                raise UserError(_(response.reason))
        except Exception as ex:
            raise UserError(ex)

    def create_api_with_bom(self, product_id):
        host = f'http://103.70.145.253:125/api/ProductMgt/GetBOM?Design={product_id.product_tmpl_id.name}'
        try:
            response = requests.get(url=host)
            if response.status_code == 200:
                for data in json.loads(response.text):
                    material_sku = self.check_design_materials_bom(data)
                    operation_id = product_id.product_tmpl_id.bom_ids[0].operation_ids.filtered(
                        lambda op: 'Weaving' in op.mapped('name'))
                    product_id.product_tmpl_id.bom_ids[0].write(
                        {'bom_line_ids': self.create_bom_line(material_sku, data.get('qty'), operation_id)})
                return product_id.product_tmpl_id.bom_ids[0]
            else:
                raise UserError(_(response.reason))
        except Exception as ex:
            raise UserError(ex)

    def check_design_materials_bom(self, data):
        materials_id = self.env['product.template'].search([('name', '=', data.get('materials'))], limit=1)
        if not materials_id:
            uom_id = self.env['uom.uom'].search([('name', '=', 'kg')], limit=1)
            materials_id = self.env['product.template'].create({
                'name': data.get('materials'),
                'uom_id': uom_id.id, 'uom_po_id': uom_id.id,
                'sale_ok': True, 'purchase_ok': True, 'is_raw_material': True,
                'detailed_type': 'product', 'invoice_policy': 'delivery',
                'raw_material_group': 'tar'
            })
            return materials_id.product_variant_ids[0]
        attrs_value = data.get('materials_Attribute_value')
        na_type = ['N/A', 'na', 'n/a', False, '', 'NULL', 'None']
        if attrs_value and attrs_value not in na_type:
            attrs_value = data.get('materials_Attribute_value').upper()
            sku = materials_id.product_variant_ids.filtered(
                lambda pv: attrs_value.strip() in pv.product_template_attribute_value_ids.mapped('name'))
            if sku:
                return sku
            return sku
        if not attrs_value or attrs_value in na_type:
            sku = self.env['product.product'].search([('product_tmpl_id', '=', materials_id.id)], limit=1)
            return sku

    def create_bom_line(self, material_sku, used_qty, operation_id):
        order_lines = []
        if material_sku:
            line_data = (0, 0, {
                "product_id": material_sku.id,
                'product_qty': float(used_qty),
                'operation_id': operation_id.id
            })
            order_lines.append(line_data)
        return order_lines

    def create_bom_design_bom(self, product_id, operation, seq, workcenter_id):
        order_lines = []
        if product_id:
            line_data = (0, 0, {
                "product_tmpl_id": product_id.id,
                'product_qty': 1,
                'operation_ids': self.create_bom_varient_operation(operation, seq, workcenter_id)
            })
            order_lines.append(line_data)
        return order_lines

    def create_bom_varient_operation(self, name, seq, workcenter_id):
        order_lines = []
        if name:
            line_data = (0, 0, {
                "workcenter_id": workcenter_id.id,
                "sequence": int(seq),
                'name': name,
            })
            order_lines.append(line_data)
        return order_lines

    def re_sync_materials(self, bom_id, product_id):
        design_components = bom_id.bom_line_ids
        boms = product_id.product_tmpl_id.bom_ids.filtered(lambda bom: bom.id != bom_id.id)
        for bom in boms:
            sku_id = bom.product_id
            operation_id = bom.operation_ids.filtered(lambda op: 'Weaving' in op.mapped('name'))
            bom.bom_line_ids.filtered(lambda bl: bl.product_id.id not in design_components.product_id.ids).unlink()
            order_lines = []
            for line in design_components:
                sku_line = bom.bom_line_ids.filtered(lambda bl: bl.product_id.id == line.product_id.id)
                if sku_line:
                    sku_line.product_qty = line.product_qty * sku_id.mrp_area
                else:
                    line_data = (0, 0, {
                        "product_id": line.product_id.id,
                        'product_qty': float(line.product_qty * sku_id.mrp_area),
                        'operation_id': operation_id.id
                    })
                    order_lines.append(line_data)
            bom.write({'bom_line_ids': order_lines
                       })

    def re_sync_operations(self, bom_id, product_id):
        boms = product_id.bom_ids.filtered(lambda bom: bom.id != bom_id.id)
        design_operations = bom_id.operation_ids
        for bom in boms:
            bom.operation_ids.filtered(
                lambda op: op.workcenter_id.id not in design_operations.workcenter_id.ids).unlink()
            for operation in design_operations:
                existing_operation = bom.operation_ids.filtered(
                    lambda op: op.workcenter_id.id == operation.workcenter_id.id)
                if existing_operation:
                    existing_operation.write({'sequence': operation.sequence})
                else:
                    bom.write({'operation_ids': [(0, 0, {'name': operation.name, 'sequence': operation.sequence,
                                                         'workcenter_id': operation.workcenter_id.id})]})

    def get_other_required_data(self, data, fields):
        value_type = {'construction': 'collection', 'collection': 'construction', 'quality': 'quality',
                      'color_way': 'color_ways', 'style': 'style', 'color': 'color',
                      'productDesignPatternName': 'pattern',
                      'content': 'contect', 'faceContent': 'face_content'}
        other_data = dict()
        for field in fields:
            value = self.env['rnd.master.data'].search([('name', '=', data.get(field)),
                                                        ('value_type', '=', value_type.get(field))], limit=1)
            if not value and data.get(field) not in ['', False]:
                value = self.env['rnd.master.data'].create({'name': data.get(field),
                                                            'value_type': value_type.get(field)})
            other_data.update({value_type.get(field): value.id})
        return False, other_data

    def check_and_get_design_data(self, data):
        design_data = {'name': data.get('design')}
        division = self.env['mrp.division'].search([('name', '=', data.get('devision').upper())], limit=1)
        uom_id = self.env['uom.uom'].search([('name', '=', 'Units')], limit=1)
        attribute_id = self.env['product.attribute'].search([('name', '=', 'size')], limit=1)
        attribute_value = self.get_size(data.get('standard'), data.get('productShapeName'), attribute_id, True)
        if not attribute_value:
            self.write({'logs_ids': [(0, 0, {'error_description': 'standard size not found', })], 'state': 'partial'})
        error, other_required_data = self.get_other_required_data(data, ['construction', 'collection', 'content',
                                                                         'quality', 'faceContent', 'style', 'color',
                                                                         'color_way', 'productDesignPatternName'])
        origin = self.env['res.country'].search([('name', '=', data.get('origins').capitalize())], limit=1)
        design_data.update(other_required_data)
        na_type = ['N/A', 'na', 'n/a', False, '', None]
        bn = 'both' if data.get('bindingPerimeter') == 'Length + Width' else data.get('bindingPerimeter')
        gp = 'both' if data.get('gachhaiPerimeter') == 'Length + Width' else data.get('gachhaiPerimeter')
        design_data.update({
            'remark': data.get('remark'),
            'trace': data.get('traceType').lower() if data.get('traceType') not in na_type else False,
            'map': data.get('mapType').lower() if data.get('mapType') not in na_type else False,
            'binding_prm': bn.lower() if data.get('bindingPerimeter') not in na_type else 'na',
            'gachhai_prm': gp.lower() if data.get('gachhaiPerimeter') not in na_type else 'na',
            'durry_prm': data.get('pattiMuraiDurry').lower() if data.get('pattiMuraiDurry') not in na_type else 'na',
            'loop_cut': data.get('loop').lower() if data.get('loop') not in na_type else 'na',
            'pile_height': float(data.get('pileHeight')) if data.get('pileHeight') else False,
            'l10n_in_hsn_code': data.get('hsn')})
        design_data.update(
            {'uom_id': uom_id.id, 'division_id': division.id, 'origin': origin.id, 'uom_po_id': uom_id.id,
             'attribute_line_ids': [(0, 0, {'attribute_id': attribute_id.id,
                                            'value_ids': [(4, attribute_value.id)]})]})
        return design_data

    def find_or_create_design(self, data):
        replenish_on_order_route = self.env['stock.route'].search([('name', '=', 'Replenish on Order (MTO)')], limit=1)
        buy_route = self.env['stock.route'].search([('name', '=', 'Buy')], limit=1)
        manufacture_route = self.env['stock.route'].search([('name', '=', 'Manufacture')], limit=1)
        if not replenish_on_order_route or not buy_route or not manufacture_route:
            raise UserError(_('Please Configure Replenish Routes'))
        design_id = self.env['product.template'].search([('name', '=', data.get('design'))], limit=1)
        if design_id:
            return design_id
        design_data = self.check_and_get_design_data(data)
        design_data.update({'route_ids': [(4, replenish_on_order_route.id), (4, buy_route.id),
                                          (4, manufacture_route.id)], 'sale_ok': True, 'purchase_ok': True,
                            'detailed_type': 'product', 'invoice_policy': 'delivery'})
        design_id = self.env['product.template'].create(design_data)
        return design_id

    @staticmethod
    def get_inno_shape(shape):
        shape_dict = {'Rectangle': 'rectangular', 'Circle': 'circle', 'Corner': 'corner', 'Cut': 'cut', 'Hmt': 'hmt',
                      'Kidney': 'kidney', 'Octa': 'octagon', 'Others': 'others', 'Oval': 'oval', 'Shape': 'shape',
                      'Shape P': 'shape_p', 'Shape R': 'shape_r', 'Square': 'square', 'Star': 'star'}
        return shape_dict.get(shape)

    def get_size(self, size, shape, attribute_id, is_standard=False):
        attr_dict = {'rectangular': '', 'circle': 'RD', 'corner': 'CO', 'cut': 'CU', 'hmt': 'HM', 'kidney': 'KD',
                     'octagon': 'OC', 'others': 'OT', 'oval': 'OV', 'shape': 'SH', 'shape_p': 'SH P',
                     'shape_r': 'SH R', 'square': 'SQ', 'star': 'ST'}
        act_size = f"{size.strip()}{attr_dict.get(self.get_inno_shape(shape))}"
        size_id = False
        if is_standard:
            size_id = self.env['product.attribute.value'].search([
                ('attribute_id', '=', attribute_id.id),
                ('name', 'ilike', act_size)], limit=1)
            if not size_id:
                id = self.create_product_size(size.strip(), attr_dict, shape)
                if id:
                    size_id = self.env['product.attribute.value'].search([
                        ('attribute_id', '=', attribute_id.id),
                        ('name', '=', id.name)], limit=1)
        else:
            size_id = self.env['inno.size'].search([('name', '=', act_size)], limit=1)
            if not size_id:
                size_id = self.create_product_size(size.strip(), attr_dict, shape)
        return size_id

    def create_product_size(self, size):
        host = 'http://103.70.145.253:125/api/ProductMgt/Size?name='
        try:
            response = requests.get(url=host + size.replace(" ", ""))
            if response.status_code == 200:
                for data in json.loads(response.text):
                    size_id = self.env['inno.size'].create({
                        'length': data.get('length'),
                        'len_fraction': data.get('lengthFraction'),
                        'width': data.get('width'),
                        'width_fraction': data.get('widthFraction'),
                        'area_sq_yard': data.get('areaYard'),
                        'is_correct': True,
                        'area': data.get('areaFeet'),
                        'perimeter': data.get('perimeter'),
                        'size_type': 'rectangular' if data.get('productShapeName').lower() == 'rectangle' else data.get(
                            'productShapeName').lower(),
                    })
                    if size_id:
                        return size_id

            else:
                raise UserError(_(response.reason))
        except Exception as ex:
            raise UserError(ex)

    def create_product_templ_record(self, data):
        design = self.find_or_create_design(data)
        attribute_id = self.env['product.attribute'].search([('name', '=', 'size')])
        attribute_value = self.get_size(data.get('standard'), data.get('productShapeName').lower(), attribute_id, True)
        sku = design.product_variant_ids.filtered(
            lambda pv: attribute_value.name in pv.product_template_attribute_value_ids.mapped('name'))
        if not sku:
            attribute_value = self.get_size(data.get('standard'), data.get('productShapeName'), attribute_id, True)
            if attribute_value:
                design.attribute_line_ids.filtered(lambda al: al.attribute_id.id == attribute_id.id).write(
                    {'value_ids': [(4, attribute_value.id)]})
            sku = design.product_variant_ids.filtered(
                lambda pv: attribute_value.name in pv.product_template_attribute_value_ids.mapped('name'))
        if sku:
            manufacturing_size = self.get_size(data.get('manufaturingSize'), data.get('productShapeName'), attribute_id)
            finishing_size = self.get_size(data.get('finishingSize'), data.get('productShapeName'), attribute_id)
            sku.write({'default_code': data.get('productname'),
                       'shape_type': self.get_inno_shape(data.get('productShapeName')),
                       'inno_mrp_size_id': manufacturing_size.id, 'inno_finishing_size_id': finishing_size.id})
        return sku

    def create_migration_records_for_weaving(self, response, api, order):
        if api in ['kelim_1', 'kelim_2']:
            ap = 'kelim'
        elif api in ['tufted_1', 'tufted_2', 'tufted_3']:
            ap = 'tufted'
        else:
            ap = api
        vals = [{'name': self.env['ir.sequence'].next_by_code('inno.migration.record'), 'data': data, 'division': ap,
                 'operation_type': order, } for data in json.loads(response) if
                not self.env['inno.migration.record'].search([('data', '=', data)])]
        if vals:
            self.create(vals)
            self._cr.commit()

    def get_weaving_order_through_api(self):
        division = ['Fattupur Tufted', 'Sarwatkhani Tufted', 'Chaksari Tufted',
                    'branch tufted',
                    'Main Tufted Finishing Weaving',
                    ]
        data = ['Fattupur', 'Sarwatkhani', 'Chaksari']
        apis = {
            'Fattupur Tufted': 'http://192.168.2.125:125/api/Weavingorder/WeavingOrderFattupurTufted?closedate=01%2FApr%2F2024',
            'Chaksari Tufted': 'http://192.168.2.125:125/api/Weavingorder/WeavingOrderChaksariTufted?closedate=01%2FApr%2F2024',
            'Sarwatkhani Tufted': 'http://192.168.2.125:125/api/Weavingorder/WeavingOrderSarwatkhaniTufted?closedate=01%2FApr%2F2024',
            #     'Main Tufted Finishing Weaving': '/WeavingOrderMainTuftedFinishingWeavingOrderOrder',
            'Main Tufted Finishing Weaving': "http://103.70.145.253:125/api/Weavingorder/WeavingOrderMainTuftedFinishingOrder?closedate=01/apr/2024",
            'branch tufted': 'http://103.70.145.253:125/api/Weavingorder/WeavingOrderMainTuftedBranch?SiteName=',
        }
        for api in division:
            try:
                if api == 'branch tufted':
                    for dt in data:
                        response = requests.get(url=apis.get(api) + f"{dt}")
                        if response.status_code == 200:
                            self.create_migration_records_for_weaving(response.text, api, 'weaving_order')
                        else:
                            raise UserError(_(response.reason))
                else:
                    response = requests.get(url=apis.get(api))
                    # response = request
                    # print(api)
                    if response.status_code == 200:
                        self.create_migration_records_for_weaving(response.text, api, 'weaving_order')
                    else:
                        raise UserError(_(response.reason))
            except Exception as ex:
                raise UserError(ex)

    def get_weaving_baazar_through_api(self):
        division = ['knotted', 'kelim', 'tufted', ]
        # host = 'http://103.70.145.253:125/api/WeavingBazar/GetWeavingBazar?Division='
        host = 'http://103.70.145.253:125/api/FinishingOrder/GetReceiveProcessInBazar_Dec?processName=weaving&Division='
        for api in division:
            try:
                response = requests.get(url=host + api)
                if response.status_code == 200:
                    self.create_migration_records_for_weaving(response.text, api, 'weaving_baazar')
                else:
                    raise UserError(_(response.reason))
            except Exception as ex:
                raise UserError(ex)

    def process_weaving_baazar(self):
        # self.process_weaving_api_record()
        for rec in self.search([('state', '=', 'draft'), ('operation_type', '=', 'weaving_baazar')]):
            new = rec.data.replace('None', '10000000000000000000000000000000000')
            data = json.loads(new.replace("'", '"'))
            partner_id = self.env['res.partner'].search([('name', '=', data.get('name'))], limit=1)
            # product_id = self.env['product.product'].search([('default_code', '=', data.get('productName'))], limit=1)
            bcodes = self.env['mrp.barcode'].search([('old_system_barcode', '=', data.get('productUidName'))])
            if bcodes and bcodes.division_id.name == data.get('divisionName'):
                baazar_id = self.env['main.baazar'].search([('parallel_receive_number', '=', data.get('jobReceiveNo')),
                                                            ('division_id', '=', bcodes.division_id.id)],
                                                           limit=1)
                main_job = False
                if not baazar_id:
                    if bcodes.main_job_work_id:
                        main_job = bcodes.main_job_work_id
                    elif (bcodes.branch_main_job_work_id):
                        main_job = bcodes.branch_main_job_work_id
                    if not partner_id:
                        if main_job:
                            partner_id = main_job.subcontractor_id
                        else:
                            partner_id = bcodes.purchase_jobwork_id.subcontractor_id
                    baazar_id = self.env['main.baazar'].sudo().create(
                        {'inno_purchase_id': bcodes.purchase_jobwork_id.id if bcodes.purchase_jobwork_id else False,
                         'parallel_receive_number': data.get('jobReceiveNo'), 'main_jobwork_id': main_job.id,
                         'subcontractor_id': partner_id.id,
                         'state': 'receiving', 'date': parser.parse(data.get('recieveDate')), })
                if baazar_id:
                    if not main_job:
                        job_work = bcodes.purchase_jobwork_id
                    else:
                        job_work = main_job
                    location = self.env['stock.location'].search([('location_id', '=', data.get('godownName'))])
                    if not baazar_id.baazar_lines_ids.filtered(lambda bcode: bcode.barcode.id == bcodes.id):
                        baazar_id.write({
                            'baazar_lines_ids': [
                                (0, 0, {'main_jobwork_id': main_job.id if main_job else False, 'state': 'verified',
                                        'barcode': bcodes.id,
                                        'inno_purchase_id': bcodes.purchase_jobwork_id.id if bcodes.purchase_jobwork_id else False,
                                        'job_work_id': job_work.jobwork_line_ids.filtered(
                                            lambda jw: bcodes.id in jw.barcodes.ids).id})],
                            'location_id': location.id if location else bcodes.location_id})
                        rec.state = 'completed'
                    else:

                        rec.write({'logs_ids': [(0, 0, {'error_description': 'Already Received',
                                                        'name': bcodes.name})], 'state': 'draft'})
            else:
                if not bcodes:
                    rec.write({'logs_ids': [(0, 0, {'error_description': 'Barcode Not found',
                                                    'name': data.get('productUidName')})], 'state': 'draft'})
                else:
                    rec.write({'logs_ids': [(0, 0, {'error_description': 'Division Wrong',
                                                    'name': data.get('divisionName')})], 'state': 'draft'})
            self._cr.commit()

    def get_pending_sale_data(self):
        host = 'http://103.70.145.253:125/api/DataMigration'
        partners = {'/GetPendingSaleOrderSuryaINC': 36, '/GetPendingSaleOrderRESTORATIONHARDWARE': 5092,
                    '/GetPendingSaleOrderSURYALIVING': 4656, '/GetPendingSaleOrderSURYACARPETFRESNO': 5094,
                    '/GetPendingSaleOrderLocalSaleOrder': 675}
        context = self._context.get('type')
        api = '/GetPendingSaleOrderSuryaINC' if context == 'surya_inc' else '/GetPendingSaleOrderRESTORATIONHARDWARE' \
            if context == 'rh' else '/GetPendingSaleOrderSURYACARPETFRESNO' if context == 'freshno' else '/GetPendingSaleOrderSURYALIVING' if context == 'living' else '/GetPendingSaleOrderLocalSaleOrder'
        try:
            response = requests.get(url=host + api)
            if response.status_code == 200:
                self.create_migration_records(response.text, partners.get(api))
            else:
                raise UserError(_(response.reason))
        except Exception as ex:
            raise UserError(ex)

    def get_current_sale_orders(self):
        partners = {'RESTORATION HARDWARE': 5092, 'Surya  Carpet  Inc': 36, 'BALAJI ART & CRAFT': 5141,
                    'SURYA CARPET PVT.LTD.': 5142, 'SURYA CARPET FRESNO': 5094, 'SURYA LIVING': 4656,
                    'EL CORTE INGLES': 1795, 'CARMEL FLOOR DESIGN LTD': 1537, 'SCI SAMPLE': 5074}
        host = 'http://103.70.145.253:125/api/DataMigration/GetCurrentSaleOrder?BuyerName='
        context = self._context.get('type')
        try:
            response = requests.get(url=host + context)
            if response.status_code == 200:
                self.create_migration_Records(response.text, partners.get(context), True)
            else:
                raise UserError(_(response.reason))
        except Exception as ex:
            raise UserError(ex)

    def create_migration_records(self, response, partmer, current_order=False):
        vals = [{'name': self.env['ir.sequence'].next_by_code('inno.migration.record'), 'data': data,
                 'operation_type': 'pending_sale', 'partner_id': partmer, 'current_order': current_order}
                for data in json.loads(response)]
        if vals:
            self.create(vals)
            self._cr.commit()

    def get_finishing_data(self):
        host = "http://103.70.145.253:125/api/FinishingOrder/GetIssueProcessInFinishing_Dec?processName="
        fetched_operation = self.search([('operation_type', '=', 'finishing')]).finishing_operation_id.ids
        for operation in self.env['mrp.workcenter'].search([('is_finishing_wc', '=', True),
                                                            ('id', 'not in', fetched_operation)]):
            try:
                response = requests.get(url=host + operation.name)
                if response.status_code == 200 and response.text:
                    self.create_finishing_records(response.text, operation)
            except Exception as ex:
                raise UserError(ex)

    def create_finishing_records(self, response, operation):
        vals = [{'name': self.env['ir.sequence'].next_by_code('inno.migration.record'), 'data': data,
                 'operation_type': "finishing", 'finishing_operation_id': operation.id} for data in
                json.loads(response)]
        if vals:
            self.create(vals)
            self._cr.commit()

    def get_finishing_bazaar(self):
        host = 'http://103.70.145.253:125/api/WeavingBazar/GetCarpetBalanceGodownWise?'
        for location in self.env['stock.warehouse'].search([]):
            for division in self.env['mrp.division'].search([]):
                try:
                    if self.search([('division', '=', division.name), ('location', '=', location.name)], limit=1):
                        continue
                    response = requests.get(url=host + f'Division={division.name}&Godown={location.name}')
                    if response.status_code == 200:
                        self.create_finishing_bazaar_records(response.text, division.name, location.name)
                except Exception as ex:
                    raise UserError(ex)

    def create_finishing_bazaar_records(self, response, division, location):
        vals = [{'name': self.env['ir.sequence'].next_by_code('inno.migration.record'), 'data': data,
                 'operation_type': "finishing_bazaar", "division": division, "location": location} for data in
                json.loads(response)]
        if vals:
            self.create(vals)
            self._cr.commit()

    def process_finishing_bazaar(self):
        for rec in self.search([('state', '!=', 'completed'), ('operation_type', '=', 'finishing_bazaar')]):
            data = json.loads(rec.data.replace("'", '"'))
            barcode = self.env['mrp.barcode'].search([('old_system_barcode', '=', data.get('productUidName'))], limit=1)
            if not barcode:
                rec.write({'logs_ids': [(0, 0, {'error_description': 'Barcode Not found in the system',
                                                'name': 'Barcode not Found'})], 'state': 'partial'})
                continue
            barcodes_in_finishing = self.env['jobwork.barcode.line'].search([('barcode_id', '=', barcode.id)])
            if not barcodes_in_finishing:
                rec.write({'logs_ids': [(0, 0, {'error_description': 'No Finishing Record found for the barcode',
                                                'name': 'No Finishing Record Found'})], 'state': 'partial'})
                continue
            operation = self.env['mrp.workcenter'].search([('name', '=', data.get('processName'))], limit=1)
            if not operation:
                rec.write(
                    {'logs_ids': [(0, 0, {'error_description': 'Operation is incorrect or not found in the system',
                                          'name': 'No Such Operation Found'})], 'state': 'partial'})
                continue
            op_finish = barcodes_in_finishing.filtered(
                lambda fin: fin.finishing_work_id.operation_id.id == operation.id)
            op_finish.state = 'done'
            is_full_finish = True if operation.name == 'Full Finishing' else False
            if not is_full_finish:
                finishing_workorder = op_finish.mrp_id.workorder_ids.filtered(
                    lambda wo: wo.workcenter_id.id == operation.id)
                finishing_workorder.finished_qty += 1
            if not op_finish.mrp_id.workorder_ids.filtered(
                    lambda wo: wo.parent_id == finishing_workorder.id) or is_full_finish:
                barcode.move_barcode_inventory()

    def process_pending_sale_purchase(self):
        mrp_route_id = self.env['stock.route'].search([('name', '=', 'Manufacture')], limit=1)
        for rec in self.env['sale.order'].search([('state', '=', 'draft')]):
            rec.order_line.write({'route_id': mrp_route_id.id})
            try:
                rec.action_confirm()
                rec.mrp_production_ids.action_confirm()
            except Exception as ex:
                pass
            self._cr.commit()

    def process_finishing_orders(self):
        for rec in self.search([('state', '!=', 'completed'), ('operation_type', '=', 'finishing')]):
            data = json.loads(rec.data.replace("'", '"'))
            barcode = self.env['mrp.barcode'].search([('old_system_barcode', '=', data.get('productUidName'))], limit=1)
            if not barcode:
                rec.write({'logs_ids': [(0, 0, {'error_description': 'Barcode Not found in the system',
                                                'name': 'Barcode not Found'})], 'state': 'partial'})
                continue
            finishing_operation = rec.finishing_operation_id \
                if rec.finishing_operation_id.name != 'Latexing Outside' \
                else self.env['mrp.workcenter'].search([('name', '=', 'Latexing')], limit=1)
            finishing_order = self.env['finishing.work.order'].search([('old_order_no', '=', data.get('docNo')),
                                                                       ('division_id', '=', barcode.division_id.id)],
                                                                      limit=1)
            if finishing_order and barcode.id in finishing_order.jobwork_barcode_lines.barcode_id.ids:
                rec.write({'logs_ids': [(0, 0, {'error_description': 'Data Already Mapped',
                                                'name': 'Already Mapped'})], 'state': 'completed'})
            elif not finishing_order:
                partner_id = self.env['res.partner'].search([('name', '=', data.get('name'))], limit=1)
                if not partner_id:
                    rec.write({'logs_ids': [(0, 0, {'error_description': 'Subcontractor Not Found in the system',
                                                    'name': 'Subcontractor not found'})], 'state': 'partial'})
                    continue
                finishing_operation.get_sequence()
                self.env['finishing.work.order'].create({
                    'subcontractor_id': partner_id.id, 'name': finishing_operation.sequence_id.next_by_id(),
                    'is_external': True if rec.finishing_operation_id.name == 'Latexing Outside' else False,
                    'operation_id': rec.finishing_operation_id.id, 'issue_date': parser.parse(data.get('docDate')),
                    'old_order_no': data.get('docNo'), 'expected_date': parser.parse(data.get('dueDate')),
                    'jobwork_barcode_lines': [(0, 0, {'barcode_id': barcode.id})]})
                barcode.state = '7_finishing'
                rec.state = 'completed'
            else:
                finishing_order.write({'jobwork_barcode_lines': [(0, 0, {'barcode_id': barcode.id})]})
                rec.state = 'completed'
                barcode.state = '7_finishing'
            self._cr.commit()

    def process_pending_sale_order(self):
        for rec in self.search([('state', '!=', 'completed'), ('operation_type', '=', 'pending_sale')]):
            data = json.loads(rec.data.replace("'", '"'))
            sale_order = self.env['sale.order'].search([('order_no', '=', data.get('saleOrderNo').replace(' ', ''))],
                                                       limit=1)
            product_id = self.env['product.product'].search([('default_code', '=', data.get('productName'))], limit=1)
            if not product_id:
                product_id = self.env['inno.sku.product.mapper'].search([
                    ('sku', '=', data.get('productName'))], limit=1).product_id
            if not product_id:
                # rec.write({'logs_ids': [(0, 0, {'error_description': 'Product not found',
                #                                 'name': data.get('name')})], 'state': 'partial'})
                # continue
                self.create_product_through_api(data.get('productName'))
                self._cr.commit()
            product_id = self.env['product.product'].search([('default_code', '=', data.get('productName'))], limit=1)
            if not product_id:
                rec.write({'logs_ids': [(0, 0, {'error_description': 'Product Not Found in the system',
                                                'name': 'Product not found'})], 'state': 'partial'})
                continue
            bom = self.env['mrp.bom'].search([('product_id', '=', product_id.id)])
            if bom:
                self.sync_bom_operations(bom)
            else:
                rec.write({'logs_ids': [(0, 0, {'error_description': 'Bom Not Found in the system',
                                                'name': 'Bom not found'})], 'state': 'partial'})
                continue
            if sale_order and sale_order.state == 'draft' and product_id:
                tax_id = False
                if rec.partner_id.id == 675:
                    if product_id.product_tmpl_id.face_content.name in ['100% Polyester', '100% Polyster']:
                        tax_id = [4, 76]
                    else:
                        tax_id = [4, 77]
                line = sale_order.order_line.filtered(lambda ol: ol.product_id.id == product_id.id)
                if line:
                    line.product_uom_qty = line.product_uom_qty + data.get('qty')
                    rec.state = 'completed'
                else:
                    sale_order.write({'order_line': [(0, 0,
                                                      {'product_id': product_id.id,
                                                       'price_unit': float(data.get('rate')), 'tax_id': tax_id,
                                                       'pending_sale_order_qty': data.get('pendingSaleOrderQty'),
                                                       'Total_sale_qty': data.get('saleOrderQty'),
                                                       'product_uom_qty': data.get('qty')})]})
                    rec.state = 'completed'
            if not sale_order and product_id:
                tax_id = False
                if rec.partner_id.id == 675:
                    if product_id.product_tmpl_id.face_content.name in ['100% Polyester', '100% Polyster']:
                        tax_id = [4, 76]
                    else:
                        tax_id = [4, 77]
                order_line = [(0, 0, {'product_id': product_id.id,
                                      'pending_sale_order_qty': data.get('pendingSaleOrderQty'),
                                      'Total_sale_qty': data.get('saleOrderQty'), 'tax_id': tax_id,
                                      'product_uom_qty': data.get('qty'),
                                      'price_unit': float(data.get('rate'))})]
                sale_order = self.env['sale.order'].create({'partner_id': rec.partner_id.id,
                                                            'order_no': data.get('saleOrderNo'),
                                                            'order_line': order_line,
                                                            'pricelist_id': rec.partner_id.property_product_pricelist.id})
                sale_order.write({'date_order': parser.parse(data.get('docDate')),
                                  'expected_date': parser.parse(data.get('dueDate'))})
                rec.state = 'completed'
            self._cr.commit()

    def merge_sale_order(self):
        sale_order = self.env['sale.order'].search([('order_no', '=', 'PO5276')])
        for rec in self.env['sale.order'].search([('order_no', '=', 'PO5276 A')]):
            rec.order_line.write({'order_id': sale_order.id})
            rec.unlink()

    def fetch_old_weaving_orders(self):
        apis = {'knotted': '/WeavingOrderMainKnotted', 'kelim': '/WeavingOrderMainKelim',
                'tufted': '/WeavingOrderMainTufted', 'Fattupur Tufted': '/WeavingOrderFattupurTufted',
                'Sarwatkhani Tufted': '/WeavingOrderSarwatkhaniTufted',
                'Chaksari Tufted': '/WeavingOrderChaksariTufted',
                'branch tufted': '/WeavingOrderMainTuftedBranch', 'Handloom Tufted': '/WeavingOrderMainTuftedHandLoom'}
        host = 'http://103.70.145.253:125/api/Weavingorder'
        api = apis.get(self._context.get('type'))
        try:
            response = requests.get(url=f"{host}{api}?closedate=01/apr/2024")
            if response.status_code == 200:
                self.create_old_weaving_records(response.text, self._context.get('type'))
        except Exception as ex:
            raise UserError(_(ex))

    def create_old_weaving_records(self, response, division):
        vals = [
            {'name': self.env['ir.sequence'].next_by_code('inno.migration.record'), 'data': data, 'division': division,
             'operation_type': 'weaving_order', } for data in json.loads(response) if
            not self.env['inno.migration.record'].search([('data', '=', data)])]
        if vals:
            self.create(vals)
            self._cr.commit()

    def fetch_account_records(self):
        api = 'http://103.70.145.253:125/api/Account/GetTrialBaance?DivisionName='
        for division in self.env['mrp.division'].search([]):
            if self.search_count([('operation_type', '=', 'account'), ('division', '=', division.name)]) == 0:
                response = requests.get(url=api + division.name)
                if response.status_code == 200:
                    vals = [
                        {'name': self.env['ir.sequence'].next_by_code('inno.migration.record'), 'data': data,
                         'division': division.name, 'operation_type': 'account', } for data in
                        json.loads(response.text)]
                    if vals:
                        self.create(vals)
                        self._cr.commit()

    def confirm_production_order(self):
        for rec in self.env['mrp.production'].search([('state', '=', 'draft')]):
            try:
                rec.action_confirm()
                self._cr.commit()
            except Exception as ex:
                raise UserError(_(ex))

    def process_migration(self):
        if not self.env['ir.config_parameter'].sudo().get_param('migration.start', False):
            self.env['ir.config_parameter'].sudo().set_param('migration.start', fields.Datetime.now())
            self._cr.commit()
        # Get pending Orders
        for partner in ['surya_inc', 'rh', 'freshno', 'living']:
            if not self.env['ir.config_parameter'].sudo().get_param(f'migration.get.pending.order{partner}', False):
                try:
                    self.with_context(type=partner).get_pending_sale_data()
                    self.env['ir.config_parameter'].sudo().set_param(f'migration.get.pending.order{partner}',
                                                                     f'Done {fields.Datetime.now()}')
                    self._cr.commit()
                except Exception as ex:
                    self.env['ir.config_parameter'].sudo().set_param(f'migration.error.get.pending.order{partner}',
                                                                     f'{ex}')
                    return
        for partner in ['RESTORATION HARDWARE', 'Surya  Carpet  Inc', 'BALAJI ART & CRAFT', 'SURYA CARPET PVT.LTD.',
                        'SURYA CARPET FRESNO', 'SURYA LIVING', 'EL CORTE INGLES', 'CARMEL FLOOR DESIGN LTD',
                        'SCI SAMPLE']:
            if not self.env['ir.config_parameter'].sudo().get_param(f'migration.get.current.order{partner}', False):
                try:
                    self.with_context(type=partner).get_current_sale_orders()
                    self.env['ir.config_parameter'].sudo().set_param(f'migration.get.current.order{partner}',
                                                                     f'Done {fields.Datetime.now()}')
                    self._cr.commit()
                except Exception as ex:
                    self.env['ir.config_parameter'].sudo().set_param(f'migration.error.get.current.order{partner}',
                                                                     f'{ex}')
                    return
        if not self.env['ir.config_parameter'].sudo().get_param('migration.process.pending.order', False):
            try:
                self.process_pending_sale_order()
                self.env['ir.config_parameter'].sudo().set_param('migration.process.pending.order',
                                                                 f'Done {fields.Datetime.now()}')
            except Exception as ex:
                self.env['ir.config_parameter'].sudo().set_param('migration.error.process.current.order', f'{ex}')
                self._cr.commit()
        if not self.env['ir.config_parameter'].sudo().get_param('migration.process.pending.order', False):
            return
        if not self.env['ir.config_parameter'].sudo().get_param('migration.confirm.pending.mrp', False):
            for rec in self.env['mrp.production'].search([('sate', '=', 'draft')]):
                try:
                    rec.action_confirm()
                    self._cr.commit()
                except Exception as ex:
                    self.env['ir.config_parameter'].sudo().set_param(f'migration.error.confirm.draft.mrp', f'{ex}')
                    return
            self.env['ir.config_parameter'].sudo().set_param(f'migration.error.confirm.draft.mrp',
                                                             f'done {fields.Datetime.now()}')
        if not self.env['ir.config_parameter'].sudo().get_param('migration.confirm.pending.mrp', False):
            return
        if not not self.env['ir.config_parameter'].sudo().get_param('migration.get.weaving.orders.dec', False):
            try:
                self.get_weaving_order_through_api()
                self.env['ir.config_parameter'].sudo().set_param(f'migration.get.weaving.orders.dec',
                                                                 f'done {fields.Datetime.now()}')
            except Exception as ex:
                self.env['ir.config_parameter'].sudo().set_param(f'migration.error.get.weaving.orders.dec', f'{ex}')
        if not self.env['ir.config_parameter'].sudo().get_param('migration.get.weaving.orders.dec', False):
            return
        for division in ['knotted', 'kelim', 'tufted', 'Fattupur Tufted', 'Sarwatkhani Tufted', 'Chaksari Tufted',
                         'branch tufted']:
            if not self.env['ir.config_parameter'].sudo().get_param(f'migration.get.weaving.order.pending{division}]',
                                                                    False):
                try:
                    self.with_context(type=division).fetch_old_weaving_orders()
                    self.env['ir.config_parameter'].sudo().set_param(f'migration.get.weaving.order.pending{division}]',
                                                                     f'done {fields.Datetime.now()}')
                except Exception as ex:
                    self.env['ir.config_parameter'].sudo().set_param(
                        f'migration.error.get.weaving.order.pending{division}', f'{ex}')
                    return
        if self.env['ir.config_parameter'].sudo().get_param(f'migration.process.weaving.orders', False):
            try:
                self.process_weaving_sale_order()
                self.env['ir.config_parameter'].sudo().set_param(f'migration.process.weaving.orders',
                                                                 f'Done {fields.Datetime.now()}')
            except Exception as ex:
                self.env['ir.config_parameter'].sudo().set_param(f'migration.error.process.weaving.order', f'{ex}')
                return
        if self.env['ir.config_parameter'].sudo().get_param(f'migration.process.weaving.orders', False):
            return

    def map_mapping(self):
        map = self.env['product.template'].search([('name', '=', 'Map')], limit=1)
        products = self.env['product.product'].sudo().search(
            [('inno_mrp_size_id', '!=', False), ('id', 'not in', map.product_variant_ids.trace_map_id.ids)])
        api = 'http://103.70.145.253:125/api/ProductMgt/Map?sku='
        for rec in products:
            response = requests.get(url=api + rec.default_code)
            if response.status_code == 200:
                attribute_id = self.env['product.attribute'].search([('name', '=', 'Map Variants')], limit=1)
                if not attribute_id:
                    raise UserError(_('Not Variant name'))
                for data in json.loads(response.text):
                    map = self.env['product.attribute.value'].search([('attribute_id', '=', attribute_id.id),
                                                                      ('name', '=', data.get('map'))],
                                                                     limit=1)
                    value = map.id if map else self.env['product.attribute.value'].create(
                        {'name': data.get('map'), 'attribute_id': attribute_id.id, }).id
                    if not map.attribute_line_ids:
                        map.update({
                            'attribute_line_ids': [
                                (0, 0, {'attribute_id': attribute_id.id,
                                        'value_ids': [
                                            (4, value)]})]})
                    else:
                        map.attribute_line_ids.filtered(
                            lambda al: al.attribute_id.id == attribute_id.id).write(
                            {'value_ids':
                                 [(4, value)]})
                    map.product_variant_ids.filtered(
                        lambda pv: data.get('map') in pv.product_template_attribute_value_ids.mapped('name')).write(
                        {'default_code': data.get('map'), 'trace_map_id': rec.id})
                self._cr.commit()

    def sync_bom_operations(self, bom):
        if not bom.operation_ids:
            response = requests.get(
                url=f'http://103.70.145.253:125/api/ProductMgt/GetProductSequence?Design={bom.product_tmpl_id.name}')
            if response.status_code == 200:
                data = json.loads(response.text)
                bom.write({'operation_ids': [(0, 0, {'name': opr.get('processName'), 'sequence': opr.get('sr'),
                                                     'workcenter_id': self.env['mrp.workcenter'].
                                              search([('name', '=', opr.get('processName'))], limit=1).id}) for opr in
                                             data]})
                self._cr.commit()

    def trace_mapping(self):
        trace = self.env['product.template'].search([('name', '=', 'Trace')], limit=1)
        products = self.env['product.product'].sudo().search(
            [('inno_mrp_size_id', '!=', False), ('id', 'not in', trace.product_variant_ids.trace_map_id.ids)])
        api = 'http://103.70.145.253:125/api/ProductMgt/Trace?sku='
        for rec in products:
            response = requests.get(url=api + rec.default_code)
            if response.status_code == 200:
                attribute_id = self.env['product.attribute'].search([('name', '=', 'Trace Variants')], limit=1)
                if not attribute_id:
                    raise UserError(_('Not Variant name'))
                if len(json.loads(response.text)) == 1:
                    for data in json.loads(response.text):
                        trace_vr = self.env['product.attribute.value'].search([('attribute_id', '=', attribute_id.id),
                                                                               ('name', '=', data.get('trace'))],
                                                                              limit=1)
                        value = trace_vr.id if trace_vr else self.env[
                            'product.attribute.value'].create(
                            {'name': data.get('trace'), 'attribute_id': attribute_id.id, }).id
                        if not trace.attribute_line_ids:
                            trace.update({
                                'attribute_line_ids': [
                                    (0, 0, {'attribute_id': attribute_id.id,
                                            'value_ids': [
                                                (4, value)]})]})
                        else:
                            trace.attribute_line_ids.filtered(
                                lambda al: al.attribute_id.id == attribute_id.id).write(
                                {'value_ids':
                                     [(4, value)]})
                        trace.product_variant_ids.filtered(
                            lambda pv: data.get('trace') in pv.product_template_attribute_value_ids.mapped(
                                'name')).write(
                            {'default_code': data.get('trace'), 'trace_map_id': rec.id})
                    self._cr.commit()

    def get_buyer_wise_sale_orders(self):
        partners = {'SURYA CARPET PVT.LTD.': 675, 'RESTORATION HARDWARE': 5092, 'Surya  Carpet  Inc': 36,
                    'BALAJI%20ART%20%26%20CRAFT': 5141, 'SURYA CARPET FRESNO': 5094, 'SURYA LIVING': 4656,
                    'EL CORTE INGLES': 1795, 'CARMEL FLOOR DESIGN LTD': 1537, 'SCI SAMPLE': 5074}
        host = f'http://103.70.145.253:125/api/DataMigration/GetPendingSaleorderBuyerWise?BuyerName='
        for key in partners.keys():
            context = key
            try:
                response = requests.get(url=host + context)
                if response.status_code == 200:
                    self.create_migration_records_inno(response.text, partners.get(context), True)
                else:
                    raise UserError(_(response.reason))
            except Exception as ex:
                raise UserError(ex)

    def create_migration_records_inno(self, response, partmer, current_order=False):
        vals = [{'name': self.env['ir.sequence'].next_by_code('inno.migration.record'), 'data': data,
                 'operation_type': 'pending_sale', 'partner_id': partmer, 'current_order': current_order}
                for data in json.loads(response) if not self.env['inno.migration.record'].search([('data', '=', data)])]
        if vals:
            self.create(vals)
            self._cr.commit()

    def process_weaving_branch_to_venodor_sale_order(self):
        product = self.env['product.product'].search([('inno_mrp_size_id', '!=', False)])
        for line in product:
            line.default_code = line.default_code.strip()
        for line in self.env['sale.order'].search([]):
            line.order_no = line.order_no.strip()
        self._cr.commit()
        for rec in self.search([('state', '=', 'draft'), ('operation_type', '=', 'weaving_order')]):
            try:
                new = rec.data.replace('None', '4')
                data = json.loads(new.replace("'", '"'))
                division = {'knotted': 'KNOTTED', 'kelim': 'KELIM',
                            'tufted': 'TUFTED', 'Fattupur Tufted': 'W.C.FATTUPUR', 'Handloom Tufted': 'TUFTED',
                            'Chaksari Tufted': 'W.C.CHAKSARI',
                            'W.C.FATTUPUR': 'W.C.FATTUPUR', 'W.C.CHAKSARI': 'W.C.CHAKSARI',
                            'W.C.SARVATKHANI': 'W.C.SARVATKHANI',
                            'Sarwatkhani Tufted': 'W.C.SARVATKHANI',
                            'Main Tufted Finishing Weaving': 'Tufted Purchase',
                            'Main kelim Finishing Weaving': 'Kelim Purchase',
                            'branch tufted': 'BRANCH TUFTED'}
                partner_id = self.env['res.partner'].search([('name', '=', data.get('name'))], limit=1)
                if not partner_id:
                    partner_id = self.env['res.partner'].create({
                        'name': data.get('name')})
                sale_order = self.env['sale.order'].search([('order_no', '=', data.get('saleOrderNo').strip())],
                                                           limit=1)
                pl = []
                for sb in self.env['sale.order'].search([]):
                    pl.append(sb.order_no)
                if not sale_order:
                    rec.write({'logs_ids': [(0, 0, {'error_description': 'Sale Order not found ',
                                                    'name': data.get('name')})], 'state': 'partial'})
                    continue
                product_id = self.env['product.product'].search(
                    [('default_code', '=', data.get('productName').strip())])
                if not product_id:
                    rec.write({'logs_ids': [(0, 0, {'error_description': 'Product Not Found ',
                                                    'name': data.get('name')})], 'state': 'partial'})
                    continue
                work_order_id = sale_order.mrp_production_ids.filtered(
                    lambda wo: wo.product_id.id == product_id.id).workorder_ids.filtered(
                    lambda wo: wo.name == 'Weaving')
                if not work_order_id:
                    rec.write({'logs_ids': [(0, 0, {'error_description': 'Work order not found ',
                                                    'name': data.get('name')})], 'state': 'partial'})
                    continue
                bcodes = self.env['mrp.barcode'].search(
                    [('old_system_barcode', '=', data.get('productUidName'))]) if sale_order else False
                if bcodes:
                    rec.write({'logs_ids': [(0, 0, {'error_description': 'Barcode already Mapped ',
                                                    'name': data.get('name')})], 'state': 'partial'})
                    continue
                if bcodes and product_id and work_order_id:
                    division_id = self.env['mrp.division'].search([('name', '=', division.get(rec.division).upper())]) \
                        if self.env['mrp.division'].search([('name', '=', division.get(rec.division).upper())]) \
                        else self.env['mrp.division'].search([('name', '=', 'TUFTED')])
                    branch_id = self.env['weaving.branch'].search([('name', '=', division.get(data.get('name')).upper()
                    if rec.division == 'branch tufted' else division.get(rec.division).upper())]) \
                        if rec.division in ['branch tufted', 'Fattupur Tufted', 'Chaksari Tufted', 'Sarwatkhani Tufted'] \
                        else False
                    if rec.division in ['knotted', 'kelim', 'tufted', 'branch tufted', 'Handloom Tufted',
                                        'Fattupur Tufted', 'Chaksari Tufted', 'Sarwatkhani Tufted']:
                        if division_id or branch_id:
                            job_work = 'main.jobwork'
                            main_jobwork_id, division_id = rec.check_main_job_work(partner_id, division_id,
                                                                                   work_order_id, data, job_work,
                                                                                   division, rec, product_id)
                            _logger.info("........ main job work - %r ........", main_jobwork_id)
                            config = self.env['inno.config'].sudo().search([], limit=1)
                            if not main_jobwork_id:
                                main_jobwork_id = self.env['main.jobwork'].create({
                                    'issue_date': data.get('docDate'),
                                    'expected_received_date': data.get('dueDate'),
                                    'loss': data.get('lossQty'),
                                    'division_id': division_id.id,
                                    'parallel_order_number': data.get('docNo'),
                                    'subcontractor_id': partner_id.id,
                                    'is_branch_subcontracting': True if branch_id else False,
                                    'weaving_center_name': branch_id.name if branch_id else False,
                                    'operation_id': work_order_id.workcenter_id.id,
                                    'reference': self.env['ir.sequence'].next_by_code('weaving.center.job.work')
                                    if rec.division in ['Fattupur Tufted', 'Chaksari Tufted', 'Sarwatkhani Tufted']
                                    else self.env['ir.sequence'].next_by_code('main.jobwork'),
                                    'allowed_chunks': config.allowed_fragments,
                                })
                            else:
                                main_jobwork_id.write(
                                    {'parallel_order_number': data.get('docNo'), 'loss': data.get('lossQty'),
                                     'issue_date': data.get('docDate'),
                                     'expected_received_date': data.get('dueDate'), })
                            if main_jobwork_id:
                                rec.check_product_with_po_branch_to_vendor_and_create(main_jobwork_id, work_order_id,
                                                                                      rec, data, product_id, branch_id,
                                                                                      'main_job_work_id', 'job_work')
            except Exception as ex:
                rec.write({'logs_ids': [(0, 0, {'error_description': ex, })], 'state': 'partial'})
            _logger.info("........ final job work - %r ........", )
            self._cr.commit()

    def check_product_with_po_branch_to_vendor_and_create(self, main_jobwork_id, work_order_id, rec, data, product_id,
                                                          branch_id, bfield, job_work):
        job_work_lines = main_jobwork_id.jobwork_line_ids.filtered(
            lambda jl: jl.product_id.id == product_id.id and jl.sale_order_number == data.get('saleOrderNo'))
        if job_work_lines:
            job_work_lines.product_qty += 1
            if work_order_id:
                job_work_lines.write({'mrp_work_order_id': work_order_id.id})
                bcodes = self.check_barcode_data(main_jobwork_id, job_work_lines, work_order_id, data,
                                                 branch_id, bfield)
                work_order_id._compute_allotment_status()
                job_work_lines.write({'barcodes': [(4, bcodes.id)]})
            _logger.info("........ check_product_with_po_and_create- %r ........")
            job_work_lines.write({'total_area': job_work_lines.area * job_work_lines.product_qty, })
            rec.write({'state': 'completed', f'{job_work}': main_jobwork_id.id})
        else:
            main_jobwork_id.write({'jobwork_line_ids': [(0, 0, {
                "mrp_work_order_id": work_order_id.id, 'issue_date': data.get('docDate'),
                "product_qty": 1, "product_id": product_id.id,
                "area": product_id.mrp_area,
                "sale_order_number": data.get('saleOrderNo'),
                'uom_id': product_id.sudo().get_rate_list_uom(work_order_id.workcenter_id),
                "total_area": product_id.mrp_area,
                'original_rate': data.get('rate'),
            })]})
            job_work_lines = main_jobwork_id.jobwork_line_ids.filtered(
                lambda jl: jl.product_id.id == product_id.id and jl.sale_order_number == data.get('saleOrderNo'))
            if work_order_id:
                if rec.division in ['Fattupur Tufted', 'Chaksari Tufted', 'Sarwatkhani Tufted']:
                    bcodes = self.check_barcode_data(main_jobwork_id, job_work_lines, work_order_id, data,
                                                     branch_id, bfield)
                    job_work_lines.write({'barcodes': [(4, bcodes.id)]})
                    job_work_lines.write({'barcodes': [(4, bcodes.id)]})
                work_order_id._compute_allotment_status()
            job_work_lines.write({
                'total_area': job_work_lines.area * job_work_lines.product_qty,
            })
            rec.write({'state': 'completed', f'{job_work}': main_jobwork_id.id})

    def release_main_job_work(self):
        main_jb = self.env['main.jobwork'].search([('state', '=', 'draft')])
        for rec in main_jb:
            rec.button_confirm()
            rec.state = 'release'
            self._cr.commit()

    def write_finsihing_mrp_size(self, size_id):
        host = 'http://103.70.145.253:125/api/ProductMgt/Size?name='
        try:
            response = requests.get(url=host + size_id.name)
            if response.status_code == 200:
                for data in json.loads(response.text):
                    size_id.write({'length': data.get('length'),
                                   'len_fraction': data.get('lengthFraction'),
                                   'width': data.get('width'),
                                   'width_fraction': data.get('widthFraction'),
                                   'area_sq_yard': data.get('areaYard'),
                                   'area': data.get('areaFeet'),
                                   'is_correct': True,
                                   'perimeter': data.get('perimeter'),
                                   'size_type': 'rectangular' if data.get(
                                       'productShapeName').lower() == 'rectangle' else data.get(
                                       'productShapeName').lower(), })
            else:
                raise UserError(_(response.reason))
        except Exception as ex:
            raise UserError(ex)
        return size_id

    def update_size_bom_and_sku(self):
        if self._context.get('update_planning'):
            products = self._context.get('order').sale_order_planning_lines.filtered(
                lambda line: line.manufacturing_qty > 0).product_id.filtered(lambda bm: not bm.is_update)
        else:
            products = self.env['product.product'].search([('default_code', '!=', False), ('is_update', '=', False)])
        for rec in products:
            host = f'http://103.70.145.253:125/api/ProductMgt/GetProductBySKU?SKU={rec.default_code}'
            response = requests.get(url=host)
            product_id = rec
            if response.status_code == 200:
                for data in json.loads(response.text):
                    if product_id:
                        mrp_size_id = self.env['inno.size'].search(
                            [('name', '=', data.get('manufaturingSize').strip().replace(" ", ""))], limit=1)
                        finishing_size_id = self.env['inno.size'].search(
                            [('name', '=', data.get('manufaturingSize').strip().replace(" ", ""))], limit=1)
                        if mrp_size_id:
                            mrp_size_id = self.write_finsihing_mrp_size(mrp_size_id)
                        if finishing_size_id:
                            mrp_size_id = self.write_finsihing_mrp_size(finishing_size_id)
                        if not mrp_size_id:
                            mrp_size_id = self.create_product_size(data.get('manufaturingSize').strip())
                        if not finishing_size_id:
                            finishing_size_id = self.create_product_size(data.get('manufaturingSize').strip())
                        product_id.write(
                            {'inno_mrp_size_id': mrp_size_id.id, 'is_update': True, 'l10n_in_hsn_code': data.get('hsn'),
                             'inno_finishing_size_id': finishing_size_id.id})
                        desgn_bom = product_id.bom_ids.filtered(lambda bm: not bm.product_id)
                        if not desgn_bom:
                            self.create_bom_and_operation(product_id)
                            boms = product_id.product_tmpl_id.bom_ids.filtered(lambda bm: not bm.product_id)
                            new_bom = boms.copy()
                            new_bom.write({'product_id': product_id.id})
                            self.re_sync_materials(boms, product_id)
                            self.re_sync_operations(boms, product_id)
                        if desgn_bom:
                            self.re_sync_materials(desgn_bom, product_id)
                            self.re_sync_operations(desgn_bom, product_id)
                    _logger.info("=============================%r============================", product_id)
                    self._cr.commit()

    def correct_mrp_orders_plan(self):
        for rec in self.env['mrp.production'].search([]).move_raw_ids:
            if not rec.bom_line_id:
                rec.product_uom_qty = rec.raw_material_production_id.bom_id.bom_line_ids.filtered(lambda
                                                                                                      bml: bml.product_id.id == rec.product_id.id).product_qty * rec.raw_material_production_id.product_uom_qty
            else:
                rec.product_uom_qty = rec.bom_line_id.product_qty * rec.raw_material_production_id.product_uom_qty

    def assign_to_data_verification(self):
        for rec in self.env['inno.research'].search([]):
            designs = rec.product_tmpl_id.filtered(lambda prd: not prd.is_verified)
            verification = self.env['inno.product.verification'].search([('product_id', '=', designs.id)], limit=1)
            if not verification:
                bom = rec.product_tmpl_id.bom_ids.filtered(lambda bom: bom.product_tmpl_id and not bom.product_id)
                self.env['inno.product.verification'].sudo().create({
                    'product_id': designs.id, 'priority': 'urgent', 'bom_id': bom.id})
            else:
                verification.sudo().write({'priority': 'urgent'})
            self._cr.commit()

    def update_sku_in_raw_materials(self):
        for rec in self.env['product.product'].search([('is_raw_material', '=', True)]):
            rec.default_code = f"{rec.name} {rec.product_template_variant_value_ids.name}"
        self._cr.commit()
        raise UserError(_("Process Finished"))

    def update_po_in_one(self, main_id, merg_ids):
        main_po = self.env['purchase.order'].browse(main_id)
        merge_pos = self.env['purchase.order'].browse(merg_ids)
        if main_po.state in ['done', 'cancel', 'purchase']:
            raise UserError(_("Can't update the main po is in done, cancel or purchsed state"))
        merge_pos.filtered(lambda po: po.state not in ['done', 'cancel', 'purchase']).order_line.write(
            {'order_id': main_id})

    def update_job_work_with_component_and_release(self, jw_id):
        job_work = self.env['main.jobwork'].browse(jw_id)
        job_work.write({'product_allotment_ids': [(0, 0, {'product_id': raw_moves.product_id.id,
                                                          'location_id': 381,
                                                          'alloted_quantity': raw_moves.product_qty,
                                                          'product_uom': raw_moves.product_uom.id}) for raw_moves in
                                                  job_work.jobwork_line_ids.mrp_work_order_id.production_id.move_raw_ids]})
        job_work.button_release_components()

    def update_rate_finishing(self):
        for rec in self.env['jobwork.barcode.line'].search([]):
            rec._compute_rate_finishing()
            rec.finishing_work_id.button_update_rate()

    def binding_gaccahai_lenght(self):
        for rec in self.env['inno.size'].search([]):
            rec.fix_binding_and_gachai_lenght()

    def remove_transfer_no(self):
        self.barcode_line.barcode_id.filtered(lambda bcode: bcode.location_id.id == 19).write({
            'location_id': self.dest_location_id.id, 'transfer_id': self.dest_location_id.id})

    def add_virtual_vendor_location(self):
        lines = self.env['jobwork.barcode.line'].search([('state', 'in', ['draft', 'rejected', 'received'])])
        if lines:
            lines.barcode_id.write({'location_id': self.env.ref('inno_finishing.stock_location_carpet_vendor_wh').id})

    #
    # def update_remaining_qty_in_weaving_bracnh(self):
    #     job_works = self.env['jobwork.allotment'].sudo().search([('id','=',69)])
    #     for rec in job_works:
    #         barcodes = rec.jobwork_id.jobwork_line_ids.barcodes.filtered(lambda br: br.id not in rec.jobwork_id.cancelled_barcodes.ids and rec.product_id.id in br.product_id.ids)
    #         rec.product_qty = len(barcodes)
    #         rec.alloted_product_qty = len(barcodes.filtered(lambda br: rec.alloted_jobwork_ids.main_jobwork_id.id in br.main_job_work_id.ids))
    #         # rec._compute_remaining_qty()

    def update_bom_operation_mo_operation(self):
        bom_lines = self.env['mrp.bom.line'].search([('operation_id', '=', False)]).filtered(
            lambda bm: bm.bom_id.product_tmpl_id.division_id and bm.bom_id.operation_ids.filtered(lambda op: 'Weaving' in op.mapped('name')))
        for bom in bom_lines.bom_id:
            operation_id = bom.operation_ids.filtered(lambda op: 'Weaving' in op.mapped('name'))
            if operation_id:
                bom.bom_line_ids.write({'operation_id': operation_id.id})
                self.env['mrp.production'].search([('bom_id', '=', bom.id), ('state', '=', 'progress')]).move_raw_ids.write(
                    {'operation_id': operation_id.id})
                self._cr.commit()
        productions = self.env['mrp.production'].search([('state', '=', 'progress')])
        for rec in productions:
            moves = rec.move_raw_ids.filtered(lambda mv: not mv.operation_id)
            for line in moves:
                work_order_id = rec.workorder_ids.filtered(lambda op: 'Weaving' in op.mapped('name'))
                line.write({'workorder_id': work_order_id.id, 'operation_id': line.bom_line_id.operation_id.id})
                self._cr.commit()

    def update_buyer_upc(self):
        line = self.env['inno.sale.order.planning.line'].search([])
        for rec in line:
            rec.update_buyer_upc()

    def update_all_data_main_and_branch(self):
        self.update_current_process()
        self.update_branch_qty()

    def update_current_process(self):
        line = self.env['mrp.barcode'].search([('state', 'in', ['2_allotment','3_allocated']),('current_process', '=', False)])
        for rec in line:
            rec.write({'current_process': rec.mrp_id.workorder_ids.filtered(lambda wr: wr.name == 'Weaving').id})
        lines = self.env['mrp.workorder'].search([])
        for wo in lines:
            wo._compute_allotment_status()

    def update_branch_qty(self):
        line = self.env['jobwork.allotment'].search([])
        for rec in line:
            rec._compute_remaining_qty()

    def update_net_wt(self):
        quants = self.env['stock.quant'].search([])
        for quant in quants:
            gross = quant.gross_weight
            net = quant.gross_weight*6/100

            nt = gross - net
            quant.write({'net_weight': nt})

    def update_gross_wt(self):
        gross = self.env['stock.quant'].search([])
        for g_wt in gross:
            size = g_wt.product_id.product_template_attribute_value_ids.product_attribute_value_id.size_id
            qty = g_wt.quantity
            inv = g_wt.invoice_group_id
            gg_wt =  qty * size.area * inv.weight
            g_wt.write({'gross_weight': gg_wt})

    def update_rate_as_per_main_order_in_barch(self):
        lines = self.env['mrp.job.work'].search([])
        for rec in lines:
            bill = self.env['account.move'].search([('job_work_id', '=',rec.main_jobwork_id.id)])
            if rec.main_jobwork_id.branch_id and not bill:
                job_line = rec.barcodes.branch_main_job_work_id.jobwork_line_ids.filtered(
                    lambda jl: rec.product_id.id in jl.product_id.ids)
                rec.write({"original_rate": job_line[0].rate if job_line else 0.00})
                rec.write({"rate": job_line[0].rate if job_line else 0.00})

    def confirm_finishing_bill(self):
        work_orders = self.env['finishing.work.order'].search([('division_id', '=', self.env.user.division_id.id)])
        for rec in work_orders:
            bill_ids = self.env['account.move'].search([('finishing_work_id', '=', rec.id),('state', '=', 'draft')])
            for bill in bill_ids:
                bill.action_post()

    def update_quality_of_productl(self):
        barcodes = self.env['mrp.barcode'].search([])
        for rec in barcodes:
            rec._compute_required_data()






