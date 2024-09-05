from odoo import models, fields, _
import logging
_logger = logging.getLogger(__name__)

class InnoMigrationLogs(models.Model):
    _name = 'inno.migration.logs'
    _description = 'Logs the success and of the migraiton'

    name = fields.Char(string='Summary')
    migration_id = fields.Many2one(comodel_name="inno.migration.record")
    migration_type = fields.Selection(selection=[('construction', 'Construction'), ('collection', 'Collection'),
                                                 ('quality', 'Quality'), ('color_ways', 'Color Ways'),
                                                 ('style', 'Style'), ('color', 'Color'), ('pattern', 'Pattern'),
                                                 ('content', 'Content'), ('face_content', 'Face Content'),
                                                 ('size', 'Size'), ('work_center', 'Work Center'),
                                                 ('division', 'Division'), ('rate_list', 'Rate List'),
                                                 ('product', 'Product'), ('consumption_product', 'Consumption Product'),
                                                 ('design_operations', 'Design Operations'), ('bom', 'BOM'),
                                                 ('bom_varient', 'BOM VARIENT'), ('contact', 'Contacts'),
                                                 ('division_operation', 'Division Operation'),
                                                 ('mapping', 'Raw Material Mapping'), ('mapper', 'SKU Mapper'),
                                                 ('update_sku', 'SKU Update'), ('product_group', 'Product Group'),
                                                 ('stock', 'Stock/Inventory'), ('update_shade', 'Update Shade'),
                                                 ('update_design', 'Design Update'), ('update_supplier', 'Supplier'),
                                                 ('weaving_barcode_mapping', 'Weaving Barcode Mapper'),
                                                 ('sale_import', 'Pending PO'), ('buyer_upc', 'Buyer UPC'),
                                                 ('update_fiscal_position', 'Update Contact'), ('import_invoice_group', 'Invoice Group')])
    data = fields.Text(string='Migration Data')
    error_description = fields.Text(string='Error Description')
    migration_status = fields.Selection(selection=[('success', 'Success'), ('failed', 'Failed')])
    rec_id = fields.Integer()
    is_resolved = fields.Boolean()

    def mark_as_resolved(self):
        shape_dict = {'Rectangle': 'rectangular', 'Circle': 'circle', 'Corner': 'corner', 'Cut': 'cut', 'Hmt': 'hmt',
                      'Kidney': 'kidney', 'Octa': 'octagon', 'Others': 'others', 'Oval': 'oval', 'Shape': 'shape',
                      'Shape P': 'shape_p', 'Shape R': 'shape_r', 'Square': 'square', 'Star': 'star'}
        attr_dict = {'rectangular': '', 'circle': 'RD', 'corner': 'CO', 'cut': 'CU', 'hmt': 'HM', 'kidney': 'KD',
                     'octagon': 'OC', 'others': 'OT', 'oval': 'OV', 'shape': 'SH', 'shape_p': 'SH P',
                     'shape_r': 'SH R', 'square': 'SQ', 'star': 'ST'}
        for rec in self:
            data = eval(rec.data)
            sku = self.env['product.product'].search([('default_code', '=', data.get('SKU'))])
            if sku and sku.shape_type and sku.inno_mrp_size_id and sku.inno_finishing_size_id:
                rec.migration_status = 'success'
                rec.is_resolved = True
            elif sku and not sku.inno_mrp_size_id or sku.inno_finishing_size_id:
                mrp_size = data.get('Manufacturing_Size')
                fin_size = data.get('Finishing_size')
                mrp_size = f"{mrp_size.strip()}{attr_dict.get(shape_dict.get(data.get('Shape')))}"
                fin_size = f"{fin_size.strip()}{attr_dict.get(shape_dict.get(data.get('Shape')))}"
                mrp_size = self.env['inno.size'].search([('name', '=', mrp_size)], limit=1)
                fin_size = self.env['inno.size'].search([('name', '=', fin_size)], limit=1)
                if not mrp_size or not fin_size:
                    continue
                sku.write({'shape_type': shape_dict.get(data.get('Shape')), 'inno_mrp_size_id': mrp_size.id,
                           'inno_finishing_size_id': fin_size.id})
                rec.migration_status = 'success'
                rec.is_resolved = True
            else:
                if self._context.get('check_logs'):
                    continue
                return {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'danger',
                        'message': "Product Not Found ",
                    }
                }

    def open_record(self):
        model_data = {'construction': 'rnd.master.data', 'collection': 'rnd.master.data', 'quality': 'rnd.master.data',
                      'color_ways': 'rnd.master.data', 'style': 'rnd.master.data', 'color': 'rnd.master.data',
                      'pattern': 'rnd.master.data', 'content': 'rnd.master.data', 'face_content': 'rnd.master.data',
                      'size': 'inno.size', 'work_center': 'mrp.workcenter', 'division': 'mrp.division',
                      'rate_list': 'inno.rate.list', 'product': 'product.product', 'mapper': 'inno.sku.product.mapper',
                      'consumption_product': 'product.product', 'design_operations': 'mrp.bom',
                      'bom': 'mrp.bom', 'bom_varient': 'mrp.bom', 'contact': 'res.partner',
                      'division_operation': 'mrp.bom', 'mapping': 'raw.material',
                      'update_sku': 'product.product','stock': 'product.product', 'update_design': 'product.template',
                      'update_supplier': 'inno.product.supplierinfo', 'sale_import': 'sale.order'}
        return {
            'name': _(type),
            'view_mode': 'form',
            'res_model': model_data.get(self.migration_type),
            'type': 'ir.actions.act_window',
            'res_id': self.rec_id
        }

    def check_and_update_all_logs(self):
        product_logs = self.search([('migration_type', '=', 'product'), ('migration_status', '=', 'failed')])
        err_dict = []
        for log in product_logs:
            data = eval(log.data)
            std_size = f"{data.get('Standard_size')} : {data.get('Shape')}"
            mrp_size = f"{data.get('Manufacturing_Size')} : {data.get('Shape')}"
            fin_size = f"{data.get('Finishing_size')} : {data.get('Shape')}"
            if std_size not in err_dict:
                err_dict.append(std_size)
            if mrp_size not in err_dict:
                err_dict.append(mrp_size)
            if fin_size not in err_dict:
                err_dict.append(fin_size)
        _logger.info(err_dict)
        # product_logs.with_context(check_logs=True).mark_as_resolved()

