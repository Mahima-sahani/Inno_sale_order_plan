from odoo import models, fields, api, _
from odoo.exceptions import UserError
import csv
import base64
import io
import logging
from dateutil import parser
_logger = logging.getLogger(__name__)


class InnoDateMigration(models.TransientModel):
    _name = 'inno.data.migration'
    _description = 'Migrate Data Using CSV file'

    operations = fields.Selection(selection=[('buyer_upc', 'Buyer UPC'), ('construction', 'Construction'), ('collection', 'Collection'),
                                             ('quality', 'Quality'), ('color_ways', 'Color Ways'),
                                             ('style', 'Style'), ('color', 'Color'), ('pattern', 'Pattern'),
                                             ('content', 'Content'), ('face_content', 'Face Content'),
                                             ('size', 'Size'), ('work_center', 'Work Center'), ('division', 'Division'),
                                             ('product', 'Product'), ('rate_list', 'Rate List'),
                                             ('consumption_product', 'Consumption Product'),
                                             ('design_operations', 'Design Operations'), ('contact', 'Contacts'),
                                             ('bom', 'BOM'), ('bom_varient', 'BOM VARIENT'),
                                             ('division_operation', 'Division Operation'), ('update_sku', 'SKU Update'),
                                             ('mapper', 'SKU Mapper'), ('product_group', 'Product Group'),
                                             ('stock', 'Stock/Inventory'), ('update_shade', 'Update Shade'),
                                             ('update_design', 'Design Update'), ('update_supplier', 'Supplier'),
                                             ('weaving_barcode_mapping', 'Weaving Barcode Mapper'),
                                             ('sale_import', 'Pending PO'), ('update_fiscal_position', 'Update Contact'),('job_worker_code', 'Job Worker Code'),
                                             ('import_invoice_group', 'Invoice Group')
                                             ])
    module_warning = fields.Char()
    file_name = fields.Char()
    data = fields.Binary(string='CSV File')
    current_count = fields.Integer(string='Current Data Count', default=0)
    raw_material_group = fields.Selection(
        selection=[('yarn', 'YARN'), ('cloth', 'CLOTH'), ('wool', 'WOOL'), ('acrlicy_yarn', 'ACRLICY YARN'),
                   ('jute_yarn', 'JUTE YARN'), ('polyster_yarn', 'POLYSTER YARN'),
                   ('wool_viscose_blend', 'WOOL VISCOSE BLEND'),
                   ('woolen_febric', 'WOOLEN FEBRIC'), ('imported', 'IMPORTED'), ('cotten_dyes', 'COTTON DYES'),
                   ('third_backing_cloth', 'THIRD BACKING CLOTH'), ('silk', 'SILK'), ('tar', 'TAR'),
                   ('tharri', 'THARRI'),
                   ('lefa', 'LEFA'), ('polypropylene', 'POLYPROPYLENE'), ('nylon', 'NYLON'), ('aanga', 'AANGA'),
                   ('ready_latex_chemical', 'READY LATEX CHEMICAL'), ('latex', 'LATEX'),
                   ('cloth_cutting', 'CLOTH CUTTING'),
                   ('newar', 'NEWAR'), ('other_raw_materials', 'OTHER RAW MATERIAL'),
                   ('weaving_cloth', 'WEAVING CLOTH'),
                   ('woolen_febric', 'WOOLEN FEBRIC'), ('cotton_cone', 'COTTON CONE')],
        string="Raw Material Group")
    rate_list_operation = fields.Many2one(comodel_name='mrp.workcenter', string='Workcenter')
    division_id = fields.Many2one(comodel_name='mrp.division', string='Division')
    rate_list_id = fields.Many2one(comodel_name='inno.rate.list', string='Rate List')
    is_outside = fields.Boolean(string='Outside?')
    is_far = fields.Boolean(string='Far?')
    uom_id = fields.Many2one(comodel_name='uom.uom', string='Unit of Measure')
    is_employee = fields.Boolean(string='Is Employee Data')

    @api.onchange('operations')
    def onchange_operations(self):
        module = ''
        self.module_warning = False
        if self.operations in ['construction', 'collection', 'quality', 'color_ways', 'style', 'color', 'pattern',
                         'content', 'face_content', 'size']:
            module = 'innorug_manufacture'
        if self.operations in ['work_center']:
            module = 'mrp'
        if module and self.env['ir.module.module'].search([('name', '=', module)]).state != 'installed':
            self.module_warning = module

    def import_data(self):
        if self.module_warning:
            raise UserError(_(f"Module {self.module_warning} is not installed in your system."))
        if not self.data and not self.rate_list_id:
            raise UserError(_("Please Import the CSV File"))
        if self.data and self.file_name.split('.')[-1] != 'csv' and not self.rate_list_id:
            raise UserError(_("Only CSV file is allowed to migrate."))
        file_content = base64.b64decode(self.data if not self.rate_list_id else '')
        reader = csv.DictReader(io.StringIO(file_content.decode('utf-8')))
        if self.operations in ['construction', 'collection', 'quality', 'color_ways', 'style', 'color', 'pattern',
                         'content', 'face_content']:
            value_type = {'construction': 'collection', 'collection': 'construction', 'quality': 'quality',
                          'color_ways': 'color_ways', 'style': 'style', 'color': 'color', 'pattern': 'pattern',
                          'content': 'contect', 'face_content': 'face_content'}
            self.import_required_product_data(reader, value_type.get(self.operations))
        if self.operations == 'size':
            self.migrate_size_data(reader)
        if self.operations == 'work_center':
            self.migrate_work_center(reader)
        if self.operations == 'division':
            self.migrate_division(reader)
        if self.operations == 'rate_list':
            self.migrate_rate_list(reader)
        if self.operations == 'product':
            self.migrate_product(reader)
            _logger.info("*********************************** Product File Imported **********************************")
        if self.operations == 'consumption_product':
            if not self.raw_material_group:
                raise UserError(_("Select raw_material_group"))
            self.migrate_consupmtion_product(reader)
        if self.operations == 'design_operations':
            self.migrate_design_operations(reader)
        if self.operations == 'bom':
            self.migrate_bom(reader)
        if self.operations == 'contact':
            self.migrate_contacts(reader)
        if self.operations == 'mapper':
            self.map_skus(reader)
        if self.operations == 'update_sku':
            self.with_context(update_sku=True).map_skus(reader)
        if self.operations == 'product_group':
            self.map_product_group(reader)
        if self.operations == 'update_shade':
            self.update_shade(reader)
        if self.operations == 'stock':
            self.update_stock(reader)
        if self.operations == 'update_design':
            self.update_design(reader)
        if self.operations == 'update_supplier':
            self.update_supplier(reader)
        if self.operations == 'weaving_barcode_mapping':
            self.map_old_barcodes(reader)
        if self.operations == 'sale_import':
            self.migrate_pending_sale_order(reader)
        if self.operations == 'update_fiscal_position':
            self.upate_fiscal_position_in_contact(reader)
        if self.operations == 'job_worker_code':
            self.upate_job_worker_code(reader)
        if self.operations == 'import_invoice_group':
            self.migrate_invoice_group(reader)
        if self.operations == 'buyer_upc':
            self.migrate_buyer_upc(reader)
        return {'type': 'ir.actions.client', 'tag': 'reload'}

    def migrate_buyer_upc(self, data_reader):
        for line, data in enumerate(data_reader):
            design = self.env['product.product'].search([('default_code', '=', data.get('ProductName'))], limit=1)
            if not design:
                design = self.env['inno.sku.product.mapper'].search([('sku', '=', data.get('ProductName'))], limit=1).product_id
            if not design:
                self.create_logs(data, 'failed', message="Product not Found")
                continue
            design.write({'buyer_upc_code': data.get('BuyerUpcCode'),
                          'buyer_specification': data.get('BuyerSpecification')})
            print(line)
            self._cr.commit()

    def migrate_invoice_group(self, data_reader):
        for data in data_reader:
            design = self.env['product.template'].search([('name', '=', data.get('Design'))], limit=1)
            if not design:
                self.create_logs(data, 'failed', message="Design not Found")
                continue
            if design.invoice_group:
                continue
            invoice_group = self.env['inno.invoive.group'].search([('name', '=', data.get('ProductInvoiceGroupName'))], limit=1)
            if not invoice_group:
                invoice_group = self.env['inno.invoive.group'].create({
                    'name': data.get('ProductInvoiceGroupName'), 'hsn_code': data.get('ItcHsCode'),
                    'rate': data.get('Rate'), 'weight': data.get('Weight'), 'knots': data.get('Knots')})
            design.invoice_group = invoice_group.id
            self._cr.commit()

    def upate_job_worker_code(self,data_reader):
        count = 0
        if [header for header in ['NAME', 'CODE',] if
            header not in data_reader.fieldnames]:
            raise UserError(_('Required data is not persent in the file.\n'
                              'Please verify the file columns and try again.'))
        for i, data in enumerate(data_reader, start=1):
            self.env['res.partner'].search([('name', '=', data.get('NAME'))], limit=1).write({'job_worker_code' : data.get('CODE')})
            self._cr.commit()

    def upate_fiscal_position_in_contact(self, data_reader):
        for data in data_reader:
            contact = self.env['res.partner'].search([('name', '=', data.get('Name'))], limit=1)
            if not contact:
                self.create_logs(data, 'failed', message="Subcontractor not Found")
            fiscal_position = self.env['account.fiscal.position'].search([('name', '=', data.get('ChargeGroupPersonName'))], limit=1)
            if not fiscal_position:
                self.create_logs(data, 'failed', message="No Such fiscal position found")
            update_record = {'property_account_position_id': fiscal_position.id}
            if contact.aadhar_no == 'NULL':
                update_record.update({'aadhar_no': False})
            if contact.pan_no == 'NULL':
                update_record.update({'pan_no': False})
            if contact.email == 'NULL':
                update_record.update({'email': False})
            contact.write(update_record)

    def migrate_pending_sale_order(self, data_reader):
        pass

    def map_old_barcodes(self, data_reader):
        count = 0
        if [header for header in ['DocNo', 'Product', 'Barcode','Loss','DueDate','IssueDate'] if header not in data_reader.fieldnames]:
            raise UserError(_('Required data is not persent in the file.\n'
                              'Please verify the file columns and try again.'))
        for i, data in enumerate(data_reader, start=1):
            try:
                order = self.env['main.jobwork'].search([('parallel_order_number', '=', data.get('DocNo'))], limit=1)
                if not order:
                    self.create_logs(data, 'failed', message='Order not found')
                order.write({'loss': data.get("Loss"), 'issue_date': parser.parse(data.get('IssueDate')),
                             'expected_received_date': parser.parse(data.get('DueDate'))})
                barcode = order.jobwork_line_ids.filtered(
                    lambda jl: jl.product_id.default_code == data.get('Product')).barcodes.filtered(
                    lambda bcode: not bcode.old_system_barcode)
                if barcode:
                    barcode[0].old_system_barcode = data.get('Barcode')
            except Exception as ex:
                self.create_logs(data, 'failed', message=ex)
            count += 1
            if count % 20 == 0:
                self.current_count = i
                self._cr.commit()

    def update_supplier(self,data_reader):
        count = 0
        if [header for header in ['Name', 'Mobile', 'Email', 'Address','Design','Units','Rate','ProcessName'] if
            header not in data_reader.fieldnames]:
            raise UserError(_('Required data is not persent in the file.\n'
                              'Please verify the file columns and try again.'))
        for i, data in enumerate(data_reader, start=1):
            if i < self.current_count + 1:
                continue
            try:
                partner = self.env['res.partner'].search([('name', '=', data.get('Name')),
                                                           ('email', '=', data.get('Email') if data.get('Email') else False)], limit=1)
                if not partner:
                    partner = self.update_partner_data(data, partner, employee=False)
                uom_dict = {'MET': 'm', 'MT2': 'm²', 'YD2': 'Sq. Yard', 'KG': 'kg', 'PCS': 'Units',
                            'Sq.Meter': 'm²', 'METER': 'm', 'FT2' : 'ft²',}
                uom_id = self.env['uom.uom'].search([('name', '=', uom_dict.get(data.get('Units')))], limit=1)
                design = self.env['product.template'].search([('name', '=', data.get('Design'))], limit=1)
                supplierinfo_id = self.env['inno.product.supplierinfo'].search([('partner_id', '=', partner.id), ('product_tmpl_id', '=', design.id)], limit=1)
                if uom_id and design and partner and not supplierinfo_id:
                    materials = {'partner_id': partner.id, 'uom_id': uom_id.id, 'product_tmpl_id': design.id,
                                 'rate': data.get('Rate'),
                                 }
                    supplierinfo_id = self.env['inno.product.supplierinfo'].create(materials)
                self.create_logs(data, 'success', rec_id=supplierinfo_id.id)
            except Exception as ex:
                self.create_logs(data, 'failed', message=ex)
            count += 1
            if count % 20 == 0:
                self.current_count = i
                self._cr.commit()

    def update_design(self,data_reader):
        count = 0
        if [header for header in ['Design', 'Construction', 'Collection', 'Content','Quality','FaceContent'] if header not in data_reader.fieldnames]:
            raise UserError(_('Required data is not persent in the file.\n'
                              'Please verify the file columns and try again.'))

        for i, data in enumerate(data_reader, start=1):
            if i < self.current_count + 1:
                continue
            try:
                design = self.env['product.template'].search([('name', '=', data.get('Design'))], limit=1)
                if design:
                    design.write({'construction': self.env['rnd.master.data'].search([('name', '=', data.get('Construction')),
                                                        ('value_type', '=', 'construction')], limit=1),
                                  'collection' : self.env['rnd.master.data'].search([('name', '=', data.get('Collection')),
                                                        ('value_type', '=', 'collection')], limit=1),
                                    'contect' : self.env['rnd.master.data'].search([('name', '=', data.get('Content')),
                                                        ('value_type', '=', 'contect')], limit=1),
                                  'quality' :  self.env['rnd.master.data'].search([('name', '=', data.get('Quality')),
                                                        ('value_type', '=', 'quality')], limit=1),
                                    'face_content' :  self.env['rnd.master.data'].search([('name', '=', data.get('FaceContent')),
                                                        ('value_type', '=', 'face_content')], limit=1)
                                            })
                self.create_logs(data, 'success',rec_id=design.id)
            except Exception as ex:
                self.create_logs(data, 'failed', message=ex)
                continue
            count += 1
            print(i)
            if count % 20 == 0:
                self.current_count = i
                self._cr.commit()

    def update_stock(self, data_reader):
        if [header for header in ['Product', 'Godown', 'Shade', 'BalQty','Units'] if header not in data_reader.fieldnames]:
            raise UserError(_('Required data is not persent in the file.\n'
                              'Please verify the file columns and try again.'))
        warehouse_dict = {warehouse.name: warehouse.code for warehouse in self.env['stock.warehouse'].search([])}
        shade_object = self.env['product.attribute.value']
        loction_dict = dict()
        for data in data_reader:
            attribute_value = False
            design = self.env['product.template'].search([('name', '=', data.get('Product'))], limit=1)
            if data.get('Shade'):
                attrs = 'SHADE'
                attribute_id = self.env['product.attribute'].search([('name', '=', attrs)], limit=1)
                if data.get('Shade') == '-':
                    atttrs_value = 'NO Shade'
                else:
                    atttrs_value = data.get('Shade').upper()
                na_type = ['N/A', 'na', 'n/a', False, '', 'NULL']
                if atttrs_value and atttrs_value not in na_type:
                    attr_val = '{"en_IN": ' + f'"{atttrs_value}", ' + '"en_US": ' + f'"{atttrs_value}"' + '}'
                    query = (f"select id from product_attribute_value where attribute_id = "
                             f"{attribute_id.id} and name::text = '{attr_val}'")
                    self.env.cr.execute(query)
                    attribute_value = self.env.cr.fetchall()
                    attribute_value = attribute_value[0][0] if attribute_value else False
                    if not attribute_value:
                        attribute_value = self.get_shade(atttrs_value, attribute_id).id
                    if design:
                        if attribute_value:
                            design.attribute_line_ids.filtered(lambda al: al.attribute_id.id == attribute_id.id).write(
                                {'value_ids': [(4, attribute_value)]})
                            if not design.attribute_line_ids:
                                self.create_attrribute_in_matrial(design, attribute_id, attribute_value)
            if not design:
                uom_dict = {'MET': 'm', 'MT2': 'm²', 'YD2': 'Sq. Yard', 'KG': 'kg', 'PCS' : 'Units', 'Sq.Meter' :'m²', 'METER' : 'm'}
                uom_id = self.env['uom.uom'].search([('name', '=', uom_dict.get(data.get('Units')))], limit=1)
                if uom_id:
                    materials = {'name': data.get('Product'), 'uom_id': uom_id.id, 'uom_po_id': uom_id.id,
                                 'sale_ok': True, 'purchase_ok': True, 'is_raw_material': True,
                                 'detailed_type': 'product', 'invoice_policy': 'delivery',
                                 'raw_material_group': self.raw_material_group
                                 }
                    design = self.env['product.template'].create(materials)
                    if attribute_value:
                        design.attribute_line_ids.filtered(lambda al: al.attribute_id.id == attribute_id.id).write(
                            {'value_ids': [(4, attribute_value)]})
                        if not design.attribute_line_ids:
                            self.create_attrribute_in_matrial(design,attribute_id, attribute_value)
            shade = shade_object.search([('id', '=', attribute_value)], limit=1)
            if not shade:
                self.create_logs(data, 'failed', message=f'Shade Not found')
                continue
            location_str = f'{warehouse_dict.get(data.get("Godown"))}/Stock'
            location_id = loction_dict.get(location_str, False)
            if not location_id:
                location_id = self.env['stock.location'].search([('complete_name', '=', location_str)], limit=1)
                if not location_id:
                    self.create_logs(data, 'failed', message=f'No Such location found in the system')
                    continue
                loction_dict[location_str] = location_id
            product_id = design.product_variant_ids.filtered(
                lambda pv: pv.product_template_attribute_value_ids.product_attribute_value_id.id == shade.id)
            if not product_id:
                self.create_logs(data, 'failed', message=f'Product not found.')
                continue
            inv_qty = data.get('BalQty')
            if inv_qty == '-':
                continue
            qty = data.get('BalQty')
            cleaned_qty = float(qty.replace(',', '').rstrip('"'))
            self.env['stock.quant']._update_available_quantity(product_id, location_id, cleaned_qty)
            self.create_logs(data, 'success',rec_id=product_id.id)
            self._cr.commit()

    def create_attrribute_in_matrial(self,design,attribute_id, attribute_value):
        if attribute_value:
            design.update({
                'attribute_line_ids': [
                    (0, 0, {'attribute_id': attribute_id.id,
                            'value_ids': [
                                (4, attribute_value)]})]})

    def update_shade(self, data_reader):
        if [header for header in ['New_value', 'Old_value'] if header not in data_reader.fieldnames]:
            raise UserError(_('Required data is not persent in the file.\n'
                              'Please verify the file columns and try again.'))
        shade_object = self.env['product.attribute.value']
        attribute_id = self.env['product.attribute'].search([('name', '=', 'SHADE')], limit=1)
        if 'Design' in data_reader.fieldnames:
            for data in data_reader:
                design = self.env['product.template'].search([('name', '=', data.get('Design'))], limit=1)
            return
        for data in data_reader:
            shade = shade_object.search([('name', '=', data.get('Old_value'))], limit=1)
            if shade:
                shade.write({'name': data.get('New_value')})
            elif not shade_object.search([('name', '=', data.get('New_value'))], limit=1):
                shade_object.create({'name': data.get('New_value'), 'attribute_id': attribute_id.id})
            self._cr.commit()

    def map_product_group(self, data_reader):
        count = 0
        operation_to_match = {'Normal Wash': ['Washing'], 'Heavy Wash': ['Washing'], 'Tufted': ['Latexing'],
                              'Handloom': ['Latexing'], 'Shag': ['Latexing'], '12/60': ['Washing'],
                              'Antique Wash': ['Washing'], 'Special Wash': ['Washing'], 'Normal Wash': ['Washing'],
                              'Washed': ['Safai'], 'Unwashed': ['Safai'], 'Design': ['Binding'], 'Plain': ['Binding'],
                              'Cotton Kelem': ['Binding'], 'Woollen': ['Streaching'], 'Acrylic': ['Streaching'],
                              'COT': ['Binding'], 'Carving': ['Full Finishing'], 'Hi-Low': ['Full Finishing'],
                              'Hard Design': ['Binding'], 'Silk Modern': ['Latexing'], 'Silk Persian': ['Latexing'],
                              'Modern': ['Full Finishing', 'Latexing'], 'Persian': ['Full Finishing', 'Latexing'],
                              'Jute': ['Washing', 'Streaching'], 'Jute Knotted': ['Binding', 'Streaching']}
        if [header for header in ['ProductRateGroupName', 'DesignName'] if header not in data_reader.fieldnames]:
            raise UserError(_('Required data is not persent in the file.\n'
                              'Please verify the file columns and try again.'))
        is_update_sku = self._context.get('update_sku')
        for i, data in enumerate(data_reader, start=1):
            if i < self.current_count + 1:
                continue
            try:
                design = self.env['product.template'].search([('name', '=', data.get('DesignName'))], limit=1)
                if not design:
                    self.create_logs(data, 'failed', message='Design not Found.')
                    continue
                group_name = data.get('ProductRateGroupName')
                group = self.env['inno.product.rate.group'].search([('rate_list_group', '=', group_name)], limit=1)
                if not group:
                    self.env['inno.product.rate.group'].create({'rate_list_group': group_name})
                workcenter_name = operation_to_match.get(group_name)
                workcenter_id = self.env['mrp.workcenter'].search([('name', 'in', workcenter_name)], limit=1).id
                if not workcenter_id:
                    self.create_logs(data, 'failed', message=f'Workcenter {workcenter_name} not Found')
                design.rate_list_id.filtered(
                    lambda rl: rl.work_center_id.id == workcenter_id).write({'rate_group_id': group.id})
                self.create_logs(data, 'success')
            except Exception as ex:
                self.create_logs(data, 'failed', message=ex)
                continue
            count += 1
            print(i)
            if count % 20 == 0:
                self.current_count = i
                self._cr.commit()

    def map_skus(self, data_reader):
        count = 0
        if [header for header in ['Design',  'Standard_size', 'SKU'] if header not in data_reader.fieldnames]:
            raise UserError(_('Required data is not persent in the file.\n'
                              'Please verify the file columns and try again.'))
        attribute_id = self.env['product.attribute'].search([('name', '=', 'size')], limit=1)
        is_update_sku = self._context.get('update_sku')
        for i, data in enumerate(data_reader, start=1):
            if i < self.current_count + 1:
                continue
            try:
                if (not is_update_sku and
                        (self.env['product.product'].search([('default_code', '=', data.get('SKU'))]) or
                         self.env['inno.sku.product.mapper'].search([('sku', '=', data.get('SKU'))]))):
                    self.create_logs(data, 'success', message='SKU Already Mapped')
                    continue
                design = self.env['product.template'].search([('name', '=', data.get('Design'))], limit=1)
                if not design:
                    self.create_logs(data, 'failed', message='Design not Found.')
                    continue
                product_id = design.product_variant_ids.filtered(
                    lambda pv: data.get('Standard_size') in pv.product_template_attribute_value_ids.mapped('name'))
                if product_id:
                    if is_update_sku:
                        product_id.default_code = data.get('SKU')
                        mapper = product_id
                    else:
                        mapper = self.env['inno.sku.product.mapper'].create({'sku': data.get('SKU'),
                                                                             'product_id': product_id.id})
                    self.create_logs(data, 'success', rec_id=mapper.id)
                else:
                    self.create_logs(data, 'failed', message="product not Found")
            except Exception as ex:
                self.create_logs(data, 'failed', message=ex)
                continue
            count += 1
            print(i)
            if count % 20 == 0:
                self.current_count = i
                self._cr.commit()

    def migrate_contacts(self, data_reader):
        count = 0
        if [header for header in ['Name', 'Mobile', 'Email', 'Address', 'BankName', 'BankBranch', 'BankCode',
                                  'AccountNo', 'Aadhar No', 'PAN No', 'Gst No', 'ProcessName'] if
            header not in data_reader.fieldnames]:
            raise UserError(_('Required data is not persent in the file.\n'
                              'Please verify the file columns and try again.'))
        for i, data in enumerate(data_reader, start=1):
            if i < self.current_count + 1:
                continue
            try:
                if not self.check_required_data(data, ['Name'], i):
                    partner = self.env['res.partner']
                    employee = self.env['hr.employee']
                    if self.is_employee:
                        employee, partner = self.search_or_create_employee(data)
                    partner = self.update_partner_data(data, partner, employee)
                    if employee:
                        employee.address_home_id = partner.id
                    self.create_logs(data, 'success', rec_id=partner.id)
            except Exception as ex:
                self.create_logs(data, 'failed', message=ex)
            count += 1
            if count % 20 == 0:
                self.current_count = i
                self._cr.commit()

    def update_partner_data(self, data, partner, employee):
        state = self.env['res.country.state'].search([('name', '=', data.get('State'))], limit=1)
        country = self.env['res.country'].search([('name', '=', data.get('Country'))], limit=1)
        if not partner:
            partner = partner.search([('name', '=', data.get('Name')), ('email', '=', data.get('Email'))], limit=1)
        if not partner:
            gst = data.get('Gst No') if data.get('Gst No') not in ['na', 'NULL', 'N/A', False, 'null', ''] else False
            partner = self.env['res.partner'].create({'name': data.get('Name'), 'email': data.get('Email'),
                                                      'mobile': data.get('Mobile'), 'street': data.get('Address'),
                                                      'city': data.get('CityName'), 'state_id': state.id,
                                                      'country_id': country.id, 'pan_no': data.get('PAN No'),
                                                      'aadhar_no': data.get('Aadhar No'), 'vat': gst,
                                                      'zip': data.get('Zipcode')})
        operation = self.env['mrp.workcenter'].search([('name', '=', data.get('ProcessName'))], limit=1)
        update_data = dict()
        if operation:
            update_data = {'operation_ids': [(4, operation.id)]}
        if not partner.bank_ids or partner.bank_ids.filtered(lambda bi: bi.acc_number != data.get('AccountNo') and bi.bank_name != data.get('BankName')):
            if data.get('AccountNo') not in ['na', 'NULL', 'N/A', '', False]:
                update_data.update({'bank_ids': [(0, 0, {'acc_holder_name': data.get('Name'),
                                                        'acc_number': data.get('AccountNo'),
                                                        'bank_name': data.get('BankName'),
                                                        'bank_bic': data.get('BankCode'),
                                                        'branch_name': data.get('BankBranch')})]})
        if data.get('ProcessName') == 'Sale':
            update_data.update({'is_buyer': True})
        if data.get('ProcessName') == 'Purchase':
            update_data.update({'is_supplier': True})
        if employee:
            update_data.update({'is_employee': True})
        else:
            update_data.update({'is_jobworker': True})
        partner.write(update_data)
        return partner

    def search_or_create_employee(self, data):
        employee = self.env['hr.employee'].search([('name', '=', data.get('Name')),
                                                    ('work_email', '=', data.get('Email'))], limit=1)
        if not employee:
            employee = self.env['hr.employee'].create({'name': data.get('Name'), 'work_email': data.get('Email'),
                                                       'mobile_phone': data.get('Mobile')})
        return employee, employee.related_contact_ids

    def delete_failed_record(self):
        if self.operations:
            logs = self.env['inno.migration.logs'].search([('migration_type', '=', self.operations),
                                                            ('migration_status', '=', 'failed')])
            if logs:
                logs.unlink()

    def delete_bom(self):
        logs = self.env['mrp.bom'].search([])
        count = 0
        while count < len(logs):
            logs[count:(count+3000)].unlink()
            count +=3000
            self._cr.commit()

    def update_second_washing(self, name):
        wc = self.env['mrp.workcenter'].search([('name', '=', name)])
        operation = self.env['mrp.routing.workcenter'].search([('name', '=', name)])
        operation.write({'workcenter_id': wc.id})

    def migrate_division_per_operation(self):
        if self.operations == 'division_operation':
            operations_dict = {'TUFTED': {'Weaving': 'Weaving', 'Washing': 'Washing', 'Second Washing': 'Washing',
                                          'Latexing': 'Latexing', 'Patti Murai': 'Patti Murai', 'Binding': 'Binding',
                                          'Clipping Embossing': 'Clipping Embossing', 'Third Backing': 'Third Backing',
                                          'Tapka Repair': 'Tapka Repair', 'Streaching': 'Streaching'},
                               'KNOTTED': {'Weaving': 'Weaving', 'First Washing': 'Washing',
                                           'First Clipping Embossing': 'Clipping Embossing',
                                           'Second Washing': 'Washing',
                                           'Second Clipping Embossing': 'Clipping Embossing',
                                           'Third Washing': 'Washing',
                                           'Streaching': 'Streaching', 'Binding': 'Binding'},
                               'KELIM': {'Weaving': 'Weaving', 'Washing': 'Washing', 'Streaching': 'Streaching',
                                         'Binding': 'Binding', 'Gachhai': 'Gachhai', 'Patti Murai': 'Patti Murai',
                                         'Safai': 'Safai'}
                               }

            products = self.env['product.template'].search([('division_id', '!=', False),
                                                        ('bom_ids', '=', False)])
            for design in products:
                if not design.bom_ids:
                    operations = [
                        (0, 0, {'name': name,
                                'workcenter_id': self.env['mrp.workcenter'].search([('name', '=', wc)], limit=1).id})
                        for name, wc in operations_dict.get(design.division_id.name).items()]
                    design.write({'bom_ids': [(0,0, {'product_qty': 1, 'operation_ids': operations})]})
                bom_id = design.bom_ids[0] if design.bom_ids else False
                if not bom_id:
                    self.create_logs('Failed', 'failed', message='Original bom not found')
                for product in design.product_variant_ids:
                    new_bom = bom_id.copy()
                    new_bom.write({'product_id': product.id})
                    self.create_logs('BOMS', 'success', rec_id=new_bom.id)
                self._cr.commit()


    def check_bom(self):
        products = self.env['product.template'].search([('is_raw_material', '=', False),
                                                        ('is_bom', '=', True)]).filtered(lambda vi: vi.bom_ids.filtered(lambda vi: not vi.bom_line_ids))
        products.write({'is_bom': False})

    def create_varient_bom(self):
        products = self.env['product.template'].search([('is_raw_material', '=', False),
                                                        ('is_bom', '=', False)])
        try:
            if products:
                for prod in products:
                    boms = prod.bom_ids
                    main_bom = boms.filtered(lambda bom: bom.product_tmpl_id.id == prod.id and not bom.product_id)
                    for variant in prod.product_variant_ids:
                        bom = boms.filtered(lambda bom: bom.product_tmpl_id.id == prod.id and bom.product_id.id == variant.id)
                        operation_id = bom.operation_ids.filtered(lambda op: 'Weaving' in op.mapped('name'))
                        bom.write({'bom_line_ids':  ([self.create_bom_line(rec.product_id, rec.product_qty*variant.mrp_area,operation_id)[0] for rec in main_bom.bom_line_ids])
                                  })
                        if bom:
                            prod.is_bom = True
                            self.create_logs('BOMS', 'success', rec_id=bom.id)
                    self._cr.commit()
        except Exception as ex:
            self.create_logs('BOM', 'failed', message=ex)

    def migrate_bom(self,data_reader):
        count = 0
        if [header for header in ['Design', 'Materials', 'matrials_Attribute','materials_Attribute_value','used_qty','Materials_units','perSq.yard(Design Based)' ] if
            header not in data_reader.fieldnames]:
            raise UserError(_('Required data is not persent in the file.\n'
                              'Please verify the file columns and try again.'))
        for i, data in enumerate(data_reader, start=1):
            if i < self.current_count + 1:
                continue
            try:
                design_id = self.env['product.template'].search([('name', '=', data.get('Design'))], limit=1)
                if not design_id:
                    self.create_logs(data, 'failed', message=f'Error in Line {i+ 1}\n> Design Name is Required')
                bom_id = design_id.bom_ids.filtered(
                    lambda bi: not bi.product_id and design_id.id in bi.product_tmpl_id.ids)
                if not bom_id:
                    self.create_logs(data, 'failed', message=f"{data.get('Design')}\n> Design Bom not found.")
                error, material_sku= self.check_design_materials_bom(data, i)
                if error:
                    continue
                if material_sku.id not in bom_id.bom_line_ids.product_id.ids:
                    if bom_id and material_sku:
                        operation_id = bom_id.operation_ids.filtered(lambda op: 'Weaving'in op.mapped('name'))
                        bom_id.write(
                            {'bom_line_ids': self.create_bom_line(material_sku, data.get('used_qty'),operation_id)
                             })
                        if bom_id:
                            self.create_logs(data, 'success', rec_id=bom_id.id)
            except Exception as ex:
                self.create_logs(data, 'failed', message=ex)
                continue
            count += 1
            if count % 20 == 0:
                self.current_count = i
                self._cr.commit()
    def create_bom_line(self,material_sku, used_qty,operation_id):
        order_lines = []
        if material_sku:
            line_data = (0, 0, {
                "product_id": material_sku.id,
                'product_qty': float(used_qty),
                'operation_id': operation_id.id
            })
            order_lines.append(line_data)
        return order_lines


    def check_design_materials_bom(self, data, line):
        materials_id = self.env['product.template'].search([('name', '=', data.get('Materials'))], limit=1)
        if not materials_id:
            self.create_logs(data, 'failed', message=f"{data.get('Materials')}\n> Materials not found.")
            return True, False
        attrs_value = data.get('materials_Attribute_value').upper()
        na_type = ['N/A', 'na', 'n/a', False, '', 'NULL']
        if attrs_value and attrs_value not in na_type :
            sku = materials_id.product_variant_ids.filtered(
                lambda pv: attrs_value.strip() in pv.product_template_attribute_value_ids.mapped('name'))
            if sku:
                return False, sku
            self.create_logs(data, 'failed', message=f"{data.get('Materials')}\n> Materials SKU not found.")
            return False, sku,
        if not attrs_value or attrs_value in na_type :
            sku = self.env['product.product'].search([('product_tmpl_id', '=', materials_id.id)], limit=1)
            return False, sku


    def migrate_design_operations(self, data_reader):
        count = 0
        if [header for header in ['Design', 'Sequence', 'Operation', ] if
            header not in data_reader.fieldnames]:
            raise UserError(_('Required data is not persent in the file.\n'
                              'Please verify the file columns and try again.'))
        for i, data in enumerate(data_reader, start=1):
            if i < self.current_count + 1:
                continue
            try:
                error, design, work_center_id = self.check_design(data, i)
                if error:
                    continue
                if design :
                    for rec in design.product_variant_ids:
                        if not design.bom_ids.filtered(lambda bi: rec.id in bi.product_id.ids and design.id in rec.product_tmpl_id.ids ):
                            design.write(
                                {'bom_ids': self.create_bom_varient_bom(data.get('Operation'),data.get('Sequence'), work_center_id, rec)
                                 })
                        bom_id =design.bom_ids.filtered(lambda bi: rec.id in bi.product_id.ids)
                        if not bom_id.operation_ids.filtered(lambda bi: bom_id.id in bi.bom_id.ids and data.get('Operation')== bi.name):
                            bom_id.write(
                                {'operation_ids': self.create_bom_varient_operation(data.get('Operation'),data.get('Sequence'), work_center_id)
                                 })
                        design_bom = design.bom_ids.filtered(lambda bi: not bi.product_id)
                        if not design_bom.operation_ids.filtered(lambda bi: data.get('Operation')== bi.name):
                            design_bom.write(
                                {'operation_ids': self.create_bom_varient_operation(data.get('Operation'),data.get('Sequence'),
                                                                                    work_center_id)
                                 })
                        if design:
                            self.create_logs(data, 'success', rec_id=bom_id)
            except Exception as ex:
                self.create_logs(data, 'failed', message=ex)
                continue
            count += 1
            if count % 20 == 0:
                self.current_count = i
                self._cr.commit()

    def create_bom_varient_bom(self, operation,seq ,workcenter_id,product_id=False):
        order_lines = []
        if product_id:
            line_data = (0, 0, {
                "product_id": product_id.id,
                'product_qty': 1,
                'operation_ids': self.create_bom_varient_operation(operation,seq ,workcenter_id)
            })
            order_lines.append(line_data)
        return order_lines


    def create_bom_design_bom(self, operation,seq, workcenter_id,product_id=False):
        order_lines = []
        if product_id:
            line_data = (0, 0, {
                "product_tmpl_id": product_id.id,
                'product_qty': 1,
                'operation_ids': self.create_bom_varient_operation(operation,seq, workcenter_id)
            })
            order_lines.append(line_data)
        return order_lines

    def create_bom_varient_operation(self, name,seq, workcenter_id):
        order_lines = []
        if name:
            line_data = (0, 0, {
                "workcenter_id": workcenter_id.id,
                "sequence" : int(seq),
                'name': name,
            })
            order_lines.append(line_data)
        return order_lines

    def check_design(self, data, line):
        if not data.get('Design'):
            self.create_logs(data, 'failed', message=f'Error in Line {line + 1}\n> Design Name is Required')
            return True, False
        design_id = self.env['product.template'].search([('name', '=', data.get('Design'))], limit=1)
        work_center_id = self.env['mrp.workcenter'].search([
            ('name', '=', data.get('Operation')),
        ], limit=1)
        if design_id and work_center_id:
            if not design_id.bom_ids.filtered(
                    lambda bi: design_id.id in bi.product_tmpl_id.ids):
                design_id.write(
                    {'bom_ids': self.create_bom_design_bom(data.get('Operation'),data.get('Sequence'), work_center_id,design_id )
                     })
        if design_id and work_center_id:
            return False, design_id, work_center_id
        return False, design_id, work_center_id

    def migrate_consupmtion_product(self,data_reader):
        count = 0
        if [header for header in ['Material_name', 'UOM', 'Attribute', 'Attribute_value',] if header not in data_reader.fieldnames]:
            raise UserError(_('Required data is not persent in the file.\n'
                              'Please verify the file columns and try again.'))
        for i, data in enumerate(data_reader, start=1):
            if i < self.current_count + 1:
                continue
            try:

                attrs = data.get('Attribute').upper()
                attribute_id = self.env['product.attribute'].search([('name', '=', attrs.strip())], limit=1)
                raw_material = self.env['raw.material'].search([('name', '=', data.get('Material_name'))], limit=1)
                if not raw_material:
                    uom_dict = {'MET': 'm', 'MT2': 'm²', 'YD2': 'Sq. Yard', 'KG': 'kg'}
                    uom_id = self.env['uom.uom'].search([('name', '=', uom_dict.get(data.get('UOM')))], limit=1)
                    if uom_id:
                        materials_data = {'name': data.get('Material_name'), 'uom_id' : uom_id.id, 'raw_material_group' : self.raw_material_group, 'raw_status': 'Unmapped'}
                        raw_material = self.env['raw.material'].create(materials_data)
                if raw_material:
                    atttrs_value = data.get('Attribute_value').upper()
                    na_type = ['N/A', 'na', 'n/a', False, '', 'NULL']
                    if atttrs_value and atttrs_value not in na_type:
                        attr_val = '{"en_IN": ' + f'"{atttrs_value}", ' + '"en_US": ' + f'"{atttrs_value}"' + '}'
                        query = (f"select id from product_attribute_value where attribute_id = "
                                 f"{attribute_id.id} and name::text = '{attr_val}'")
                        self.env.cr.execute(query)
                        attribute_value = self.env.cr.fetchall()
                        attribute_value = attribute_value[0][0] if attribute_value else False
                        if not attribute_value:
                            attribute_value = self.get_shade(data.get('Attribute_value'), attribute_id).id
                        if attribute_value and attribute_value not in raw_material.material_lines.attribute_value.ids:
                            raw_material.write({'material_lines': [(0, 0, {'shade': attrs.strip(), 'attribute' :atttrs_value ,
                                                                           'shade_id':attribute_id.id, 'attribute_value' : attribute_value,})]})
            except Exception as ex:
                self.create_logs(data, 'failed', message=ex)
                continue
            count += 1
            if count % 20 == 0:
                self.current_count = i
                self._cr.commit()

    def migrate_product(self, data_reader):
        count = 0
        if [header for header in ['Design', 'UOM', 'Product_name', 'Shape', 'Standard_size', 'Manufacturing_Size',
                                  'Finishing_size', 'Construction', 'Collection', 'Content', 'Quality', 'FaceContent',
                                  'Style', 'Color', 'Color_ways', 'Division', 'Design pattern', 'Remarks', 'Origin',
                                  'Trace Type', 'Map Type', 'Binding Parm', 'Gachhai Param', 'Durry Param', 'SKU',
                                  'Pile Height', 'Loop Cut'] if header not in data_reader.fieldnames]:
            raise UserError(_('Required data is not persent in the file.\n'
                              'Please verify the file columns and try again.'))
        for i, data in enumerate(data_reader, start=1):
            if i < self.current_count + 1:
                continue
            try:
                error, design = self.find_or_create_design(data, i)
                if error:
                    continue
                attribute_id = self.env['product.attribute'].search([('name', '=', 'size')])
                attribute_value = self.get_size(data.get('Standard_size'), data.get('Shape'), attribute_id, True)
                sku = design.product_variant_ids.filtered(
                    lambda pv: attribute_value.name in pv.product_template_attribute_value_ids.mapped('name'))
                if not sku:
                    attribute_value = self.get_size(data.get('Standard_size'), data.get('Shape'), attribute_id, True)
                    if not attribute_value:
                        self.create_logs(data, 'failed', message=f"Error in Line {i}\n> Standard size Data not "
                                                                 f"found in the System.")
                        continue
                    design.attribute_line_ids.filtered(lambda al: al.attribute_id.id == attribute_id.id).write({'value_ids': [(4, attribute_value.id)]})
                    sku = design.product_variant_ids.filtered(
                        lambda pv: attribute_value.name in pv.product_template_attribute_value_ids.mapped('name'))
                if sku:
                    manufacturing_size = self.get_size(data.get('Manufacturing_Size'), data.get('Shape'), attribute_id)
                    finishing_size = self.get_size(data.get('Finishing_size'), data.get('Shape'), attribute_id)
                    if not manufacturing_size:
                        self.create_logs(data, 'failed', message=f'Error in Line {i + 1}\n> Manufacturing size '
                                                                 f'Data Not found in the System.')
                    if not finishing_size:
                        self.create_logs(data, 'failed', message=f'Error in Line {i + 1}\n> Finishing size '
                                                                 f'Data Not found in the System.')
                    sku.write({'default_code': data.get('SKU'), 'shape_type': self.get_inno_shape(data.get('Shape')),
                               'inno_mrp_size_id': manufacturing_size.id, 'inno_finishing_size_id': finishing_size.id})
                    self.create_logs(data, 'success', rec_id=sku.id)
            except Exception as ex:
                self.create_logs(data, 'failed', message=ex)
                continue
            count += 1
            print(i)
            if count % 20 == 0:
                self.current_count = i
                self._cr.commit()

    def get_size(self, size, shape, attribute_id, is_standard=False):
        attr_dict = {'rectangular': '', 'circle': 'RD', 'corner': 'CO', 'cut': 'CU', 'hmt': 'HM', 'kidney': 'KD',
                     'octagon': 'OC', 'others': 'OT', 'oval': 'OV', 'shape': 'SH', 'shape_p': 'SH P',
                     'shape_r': 'SH R', 'square': 'SQ', 'star': 'ST'}
        act_size = f"{size.strip()}{attr_dict.get(self.get_inno_shape(shape))}"
        size_id = False
        if is_standard:
            size_id = self.env['product.attribute.value'].search([
                ('attribute_id', '=', attribute_id.id),
                ('name', '=', act_size)], limit=1)
        else:
            size_id = self.env['inno.size'].search([('name', '=', act_size)], limit=1)
        return size_id

    @staticmethod
    def get_inno_shape(shape):
        shape_dict = {'Rectangle': 'rectangular', 'Circle': 'circle', 'Corner': 'corner', 'Cut': 'cut', 'Hmt': 'hmt',
                      'Kidney': 'kidney', 'Octa': 'octagon', 'Others': 'others', 'Oval': 'oval', 'Shape': 'shape',
                      'Shape P': 'shape_p', 'Shape R': 'shape_r', 'Square': 'square', 'Star': 'star'}
        return shape_dict.get(shape)

    def find_or_create_design(self, data, line):
        if not data.get('Design'):
            self.create_logs(data, 'failed', message=f'Error in Line {line+1}\n> Design Name is Required')
            return True, False
        replenish_on_order_route = self.env['stock.route'].search([('name', '=', 'Replenish on Order (MTO)')], limit=1)
        buy_route = self.env['stock.route'].search([('name', '=', 'Buy')], limit=1)
        manufacture_route = self.env['stock.route'].search([('name', '=', 'Manufacture')], limit=1)
        if not replenish_on_order_route or not buy_route or not manufacture_route:
            raise UserError(_('Please Configure Replenish Routes'))
        design_id = self.env['product.template'].search([('name', '=', data.get('Design'))], limit=1)
        if design_id:
            return False, design_id
        error, design_data = self.check_and_get_design_data(data, line)
        if error:
            return True, False
        design_data.update({'route_ids': [(4, replenish_on_order_route.id), (4, buy_route.id),
                                          (4, manufacture_route.id)], 'sale_ok': True, 'purchase_ok': True,
                            'detailed_type': 'product', 'invoice_policy': 'delivery'})
        design_id = self.env['product.template'].create(design_data)
        self._cr.commit()
        return False, design_id

    def find_or_create_materials(self, data, line,atribute_id, attribute_value):
        if not data.get('Material_name'):
            self.create_logs(data, 'failed', message=f'Error in Line {line+1}\n> Material Name is Required')
            return True, False
        replenish_on_order_route = self.env['stock.route'].search([('name', '=', 'Replenish on Order (MTO)')], limit=1)
        buy_route = self.env['stock.route'].search([('name', '=', 'Buy')], limit=1)
        if not replenish_on_order_route or not buy_route:
            raise UserError(_('Please Configure Replenish Routes'))
        error, design_data = self.check_and_get_materials_data(data, line, atribute_id, attribute_value)
        if error:
            return True, False
        design_data.update({'route_ids': [(4, replenish_on_order_route.id), (4, buy_route.id),], 'sale_ok': True, 'purchase_ok': True, 'is_raw_material' : True,
                            'detailed_type': 'product', 'invoice_policy': 'delivery', 'raw_material_group': self.raw_material_group})
        design_id = self.env['product.template'].create(design_data)
        self._cr.commit()
        return False, design_id

    def check_and_get_materials_data(self, data, line, attribute_id, attribute_value):
        materials_data = {'name': data.get('Material_name')}
        if self.check_required_data(data, ['UOM', 'Attribute', 'Attribute_value',], line):
            return True, False
        uom_dict = {'MET': 'm', 'MT2': 'm²', 'YD2': 'Sq. Yard', 'KG': 'kg'}
        uom_id = self.env['uom.uom'].search([('name', '=', uom_dict.get(data.get('UOM')))], limit=1)
        if not uom_id:
            self.create_logs(data, 'failed', message=f'Error in Line {line + 1}\n> UOM data Not found in '
                                                     f'the System')
            return True, False
        if attribute_value:
            materials_data.update({
                'attribute_line_ids': [
                    (0, 0, {'attribute_id': attribute_id.id,
                            'value_ids': [
                                (4, attribute_value)]})]})
        materials_data.update(
            {'uom_id': uom_id.id, 'uom_po_id': uom_id.id,})
        return False, materials_data

    def get_shade(self, attribute_value, attribute_id):
        attribute_value_id = self.env['product.attribute.value'].search([
            ('attribute_id', '=', attribute_id.id),
            ('name', '=', attribute_value.strip())], limit=1)
        if not attribute_value_id:
            attribute_value_id =self.env['product.attribute.value'].create({
                'name': attribute_value.strip(),
                'attribute_id': attribute_id.id,
            })
        return attribute_value_id

    def check_and_get_design_data(self, data, line):
        design_data = {'name': data.get('Design')}
        if self.check_required_data(data, ['UOM', 'Standard_size', 'Construction', 'Collection', 'Content',
                                           'Quality', 'FaceContent', 'Color', 'Division', 'Origin', 'Shape',
                                           'Manufacturing_Size', 'Finishing_size', 'SKU', 'Product_name'], line):
            return True, False
        division = self.env['mrp.division'].search([('name', '=', data.get('Division').upper())], limit=1)
        if not division:
            self.create_logs(data, 'failed', message=f'Error in Line {line + 1}\n> Division data Not'
                                                     f' found in the System')
            return True, False
        uom_id = self.env['uom.uom'].search([('name', '=', data.get('UOM'))], limit=1)
        if not uom_id:
            self.create_logs(data, 'failed', message=f'Error in Line {line + 1}\n> UOM data Not found in '
                                                     f'the System')
            return True, False
        attribute_id = self.env['product.attribute'].search([('name', '=', 'size')], limit=1)
        attribute_value = self.get_size(data.get('Standard_size'), data.get('Shape'), attribute_id, True)
        if not attribute_value:
            self.create_logs(data, 'failed', message=f'Error in Line {line + 1}\n> standard size data Not'
                                                     f' found in the System')
            return True, False
        error, other_required_data = self.get_other_required_data(data, ['Construction', 'Collection', 'Content',
                                                                         'Quality', 'FaceContent', 'Style', 'Color',
                                                                         'Color_ways', 'Design pattern'], line)
        if error:
            return True, False
        origin = self.env['res.country'].search([('name', '=', data.get('Origin').capitalize())], limit=1)
        if not origin:
            self.create_logs(data, 'failed', message=f'Error in Line {line + 1}\n> Origin data Not'
                                                     f' found in the System')
            return True, False
        design_data.update(other_required_data)
        na_type = ['N/A', 'na', 'n/a', False, '']
        design_data.update({
            'remark': data.get('Remarks'),
            'trace': data.get('Trace Type').lower() if data.get('Trace Type') not in na_type else False,
            'map': data.get('Map Type').lower() if data.get('Map Type') not in na_type else False,
            'binding_prm': data.get('Binding Parm').lower() if data.get('Binding Parm') not in na_type else 'na',
            'gachhai_prm': data.get('Gachhai Param').lower() if data.get('Gachhai Param') not in na_type else 'na',
            'durry_prm': data.get('Durry Param').lower() if data.get('Durry Param') not in na_type else 'na',
            'loop_cut': data.get('Loop Cut').lower() if data.get('Loop Cut') not in na_type else 'na',
            'pile_height': float(data.get('Pile Height')) if data.get('Pile Height') else False,
            'l10n_in_hsn_code': data.get('HSN/SAC Code')})
        design_data.update({'uom_id': uom_id.id, 'division_id': division.id, 'origin': origin.id, 'uom_po_id': uom_id.id,
                     'attribute_line_ids': [(0, 0, {'attribute_id': attribute_id.id,
                                                    'value_ids': [(4, attribute_value.id)]})]})
        return False, design_data

    def get_other_required_data(self, data, fields, line):
        value_type = {'Construction': 'collection', 'Collection': 'construction', 'Quality': 'quality',
                      'Color_ways': 'color_ways', 'Style': 'style', 'Color': 'color', 'Design pattern': 'pattern',
                      'Content': 'contect', 'FaceContent': 'face_content'}
        other_data = dict()
        for field in fields:
            value = self.env['rnd.master.data'].search([('name', '=', data.get(field)),
                                                        ('value_type', '=', value_type.get(field))], limit=1)
            if not value and data.get(field) not in ['', False]:
                value = self.env['rnd.master.data'].create({'name': data.get(field),
                                                            'value_type': value_type.get(field)})
            if not value and field not in ['Style', 'Design pattern', 'Color_ways']:
                self.create_logs(data, 'failed', message=f'Error in Line {line + 1}\n> {field}: {data.get(field)}'
                                                         f' Not found in the System')
                return True, False
            other_data.update({value_type.get(field): value.id})
        return False, other_data

    def create_logs(self, data, type, rec_id=False, message=''):
        self.env['inno.migration.logs'].create({
            'name': f"{self.env['ir.sequence'].next_by_code('inno.migrate.logs')}/{self.operations}",
            'migration_status': type, 'error_description': message,
            'migration_type': self.operations, 'data': data, 'rec_id': rec_id})

    def migrate_rate_list(self, data_reader):
        count = 0
        if data_reader.fieldnames:
            if [header for header in ['Design', 'Rate', 'Loss'] if header not in data_reader.fieldnames]:
                raise UserError(_('Required data is not persent in the file.\n'
                                  'Please verify the file columns and try again.'))
            for i, data in enumerate(data_reader, start=1):
                if i < self.current_count+1:
                    continue
                if not self.rate_list_id:
                    if self.check_required_data(data, ['Design', 'Rate', 'Loss']):
                        continue
                    try:
                        design = self.env['product.template'].search([('name', '=', data.get('Design'))], limit=1)
                        if not design:
                            self.create_logs(data, 'failed', message='Design Not Found')
                        price_list = self.env['inno.rate.list'].create({'name': f"{self.rate_list_operation.name}_rate_{data.get('Design')}",
                                                                        'base_price': float(data.get('Rate')),
                                                                        'loss': float(data.get('Loss')) if data.get('Loss') != '-' else 0.00})
                        uom = self.env['uom.uom'].search([('name', '=', 'Sq. Yard')], limit=1)
                        design.write({'rate_list_id': [(0, 0, {'work_center_id': self.rate_list_operation.id,
                                                               'uom_id': uom.id if not self.uom_id else self.uom_id.id,
                                                               'price_list_id': price_list.id})]})
                        self.create_logs(data, 'success', rec_id=price_list.id)
                    except Exception as ex:
                        self.create_logs(data, 'failed', message=ex)
        else:
            designs = self.env['product.template'].search([('division_id', '=', self.division_id.id)])
            designs.write({'rate_list_id': [(0, 0, {'work_center_id': self.rate_list_operation.id,
                                                    'uom_id': self.uom_id.id, 'price_list_id': self.rate_list_id.id,
                                                    'is_outside': self.is_outside, 'is_far': self.is_far})]})
            count += 1
            if count % 20 == 0:
                self.current_count = i
                self._cr.commit()

    def migrate_division(self, data_reader):
        if [header for header in ['Name'] if header not in data_reader.fieldnames]:
            raise UserError(_('Required data is not persent in the file.\n'
                              'Please verify the file columns and try again.'))
        for data in data_reader:
            if self.check_required_data(data, ['Name']):
                continue
            try:
                rec = self.env['mrp.division'].create({'name': data.get('Name')})
                self.create_logs(data, 'success', rec_id=rec.id)
            except Exception as ex:
                self.create_logs(data, 'failed', message=ex)

    def migrate_work_center(self, data_reader):
        if [header for header in ['Name', 'Code', 'Is_weaving'] if header not in data_reader.fieldnames]:
            raise UserError(_('Required data is not persent in the file.\n'
                              'Please verify the file columns and try again.'))
        for data in data_reader:
            if self.check_required_data(data, ['Name', 'Code']):
                continue
            try:
                rec = self.env['mrp.workcenter'].create({'name': data.get('Name'), 'code': data.get('Code'),
                                                   'is_finishing_wc': not bool(int(data.get('Is_weaving')))})
                self.create_logs(data, 'success', rec_id=rec.id)
            except Exception as ex:
                self.create_logs(data, 'failed', message=ex)

    def migrate_size_data(self, data_reader):
        count = 0
        if [header for header in ['Size Name', 'Shape', 'Length', 'Width', 'Area(Sq. Yard)',
                                  'Length Fraction', 'Width Fraction', 'Area(Sq.Feet)',
                                  'Perimeter'] if header not in data_reader.fieldnames]:
            raise UserError(_('Required data is not persent in the file.\n'
                              'Please verify the file columns and try again.'))
        size_attrib = self.env['product.attribute'].search([('name', '=', 'size')], limit=1)
        if not size_attrib:
            size_attrib = self.env['product.attribute'].create({'name': 'size', 'display_type': 'radio',
                                                                'create_variant': 'always'})
        shape_dict = {'Rectangle': 'rectangular', 'Circle': 'circle', 'Corner': 'corner', 'Cut': 'cut', 'Hmt': 'hmt',
                      'Kidney': 'kidney', 'Octa': 'octagon', 'Others': 'others', 'Oval': 'oval', 'Shape': 'shape',
                      'Shape P': 'shape_p', 'Shape R': 'shape_r', 'Square': 'square', 'Star': 'star'}
        for i, data in enumerate(data_reader, start=1):
            if i < self.current_count+1:
                continue
            if self.env['inno.size'].search([('name', '=', data.get('Size Name').strip())]):
                continue
            if self.check_required_data(data, ['Size Name', 'Shape', 'Length', 'Width','Area(Sq. Yard)',
                                               'Area(Sq.Feet)', 'Perimeter'], i):
                continue
            try:
                rec = self.env['inno.size'].create({'name': data.get('Size Name').strip(),
                                                    'size_type': shape_dict.get(data.get('Shape')),
                                                    'length': int(data.get('Length')), 'width': int(data.get('Width')),
                                                    'len_fraction': float(data.get('Length Fraction')) if
                                                    data.get('Length Fraction') else 0.0,
                                                    'width_fraction': float(data.get('Width Fraction')) if
                                                    data.get('Width Fraction') else 0.0,
                                                    'area_sq_yard': float(data.get('Area(Sq.Feet)')),
                                                    'area': float(data.get('Area(Sq.Feet)')),
                                                    'perimeter': float(data.get('Perimeter'))})
                self.create_logs(data, 'success', rec_id=rec.id)
            except Exception as ex:
                self.create_logs(data, 'failed', message=ex)
                continue
            self.env['product.attribute.value'].create({'attribute_id': size_attrib.id,
                                                        'name': data.get('Size Name').strip(), 'size_id': rec.id})
            count += 1
            if count % 20 == 0:
                self.current_count = i
                self._cr.commit()

    def import_required_product_data(self, data_reader, value):
        count = 0
        if "Name" not in data_reader.fieldnames:
            raise UserError(_('Required data is not persent in the file.\n'
                              'Please verify the file columns and try again.'))
        for i, data in enumerate(data_reader, start=1):
            if i < self.current_count+1:
                continue
            record = self.env['rnd.master.data'].search([('name', '=', data.get('Name')), ('value_type', '=', value)])
            if record:
                if value == 'quality':
                    record.write({'weight': float(data.get('Weight'))})
                count += 1
                continue
            else:
                rec = self.env['rnd.master.data'].create({
                    'name': data.get('Name'), 'value_type': value, 'weight': data.get('Weight')
                })
                self.create_logs(data, 'success', rec_id=rec.id)
                count += 1
            if count % 20 == 0:
                self.current_count = i
                self._cr.commit()

    def check_required_data(self, data, field_check, line=False):
        error = [f"Data in column {field} is required" for field in field_check if not data.get(field)]
        if error:
            error = '\n> '.join(error)
            message = f'Error in line {line+1} \n {error}' if line else error
            self.create_logs(data, 'failed', message=message)
            return True
        return False


    def download_sample(self):
        url = self.get_download_url(self.operations)
        if url:
            return {
                'type': 'ir.actions.act_url',
                'url': url
            }
        else:
            return False

    @staticmethod
    def get_download_url(operation):
        sample_files = {'size': 'size_data'}
        if operation in ['construction', 'collection', 'quality', 'color_ways', 'style', 'color', 'pattern',
                         'content', 'face_content']:
            return '/inno_data_migration/static/files/required_product_data.csv'
        else:
            return f'/inno_data_migration/static/files/{operation}.csv'
