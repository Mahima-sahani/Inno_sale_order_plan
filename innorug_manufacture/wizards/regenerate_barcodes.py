from odoo import models, fields, _, api
from odoo.exceptions import UserError, ValidationError, MissingError
import csv
import base64
import io
import logging
from odoo import http
from odoo import modules, tools
_logger = logging.getLogger(__name__)


class ReGenerateBarcodes(models.TransientModel):
    _name = 'mrp.barcode.regenerate'
    _description = 'help to add lost penalty'

    def _barcode_domain(self):
        barcodes = self._context.get('barcodes')
        if barcodes:
            return [('id', 'in', barcodes)]
        else:
            return []

    print_all_barcodes = fields.Boolean(string="Print All Barcodes")
    barcodes = fields.Many2many(comodel_name='mrp.barcode', domain=_barcode_domain)
    file_name = fields.Char()
    data = fields.Binary(string='CSV File')
    upload = fields.Selection([
        ('product', 'UPLOAD PRODUCT'),
        ('consumption', 'UPLOAD CONSUMPTION'),
        ('bom', 'UPLOAD BOM'),
    ], string='UPLOAD')
    barcode_reprint_penalty = fields.Integer()

    @api.model
    def default_get(self, fields_list):
        rec = super().default_get(fields_list)
        penalty = self.env['inno.config'].sudo().search([], limit=1).barcode_reprint_penalty
        rec.update({'barcode_reprint_penalty': penalty})
        return rec

    def regenerate_barcodes(self):
        """
        Will add penalty to barcodes and download the barcodes.
        """
        main_jobwork=self.env['main.jobwork'].browse(self._context.get('active_id'))
        if self.print_all_barcodes:
            barcodes = main_jobwork.jobwork_line_ids.barcodes
        else:
            barcodes = self.barcodes
        if barcodes:
            barcodes = barcodes.filtered(lambda br: br.id not in main_jobwork.cancelled_barcodes.ids)
            for barcode in barcodes:
                barcode.write({'pen_inc_ids': [(0, 0, {'type': 're_printing', 'record_date': fields.Datetime.now(),
                                                       'amount': self.barcode_reprint_penalty,
                                                       'rec_id': self._context.get('active_id'),
                                                       'model_id': self.env.ref('innorug_manufacture.model_main_jobwork').id
                                                       })]})
            report = self.env.ref('innorug_manufacture.action_report_print_barcode',
                                  raise_if_not_found=False).report_action(docids=barcodes.ids)
            return report
    
    def do_import(self):
        file_content = base64.b64decode(self.data)
        reader = csv.DictReader(io.StringIO(file_content.decode('utf-8')))
        replenish_on_order_route = self.env['stock.route'].search([('name', '=', 'Replenish on Order (MTO)')], limit=1)
        buy_route = self.env['stock.route'].search([('name', '=', 'Buy')], limit=1)
        manufacture_route = self.env['stock.route'].search([('name', '=', 'Manufacture')], limit=1)
        
        if self.upload == 'product' or self.upload == "consumption":
            for row in reader:
                _logger.info("~~~~~~%r~~~", row.get("Design"))
                division_id = self.env['mrp.division'].search([('name', '=', row.get('Division'))], limit=1)
                if not division_id:
                    division_id = self.env['mrp.division'].create({
                        'name': row.get('Division'),
                    })
                _logger.info("~~~~~~%r~~1~", row.get("Unit of Measure"))
                uom_id = self.env['uom.uom'].search([('name', '=', row.get('Unit of Measure'))], limit=1)
                _logger.info("~~~~~~%r4444~22222~~", row.get(uom_id.name))
                if not uom_id:
                    uom_id = self.env['uom.uom'].create({
                        'name': row.get('Unit of Measure'),
                    })
                _logger.info("~~~~~~%r~22222~~", row.get(uom_id.name))
                _logger.info("~~~~~~%r~~~~", row.get('QC'))


                product_template = self.env['product.template'].search([('name', '=', row.get('Design'))], limit=1)
                if not product_template:
                    product_template = self.env['product.template'].create({
                        'name': row.get('Design'),
                        'division_id': division_id.id,
                        'uom_id': uom_id.id,
                        'uom_po_id': uom_id.id,
                        # 'sale_ok': row.get('Can be Sold'),
                        # 'purchase_ok': row.get('Can be Purchased'),
                        # 'costruction': row.get('Construction'),
                        # 'collection': row.get('Collection'),
                        # 'quality': row.get('Quality'),
                        # 'style': row.get('Style'),
                        # 'design_pattern': row.get('design_pattern'),
                        # 'content': row.get('Content'),
                        # 'face_content': row.get('FaceContent'),
                        # 'detailed_type' : 'product',
                        # 'colour' : row.get('colour'),
                        # 'colour_ways': row.get('colour_ways'),
                        # 'process_sequence': row.get('process_sequence'),

                    })

                attribute = self.env['product.attribute'].search([('name', '=',  row.get('attribute_name'))], limit=1)
                if not attribute:
                    attribute = self.env['product.attribute'].create({
                        'name':  row.get('attribute_name'),
                        'create_variant': 'always',
                    })

                attribute_value = self.env['product.attribute.value'].search([
                    ('attribute_id', '=', attribute.id),
                    ('name', '=', row.get('Standard_size/Value')),
                ], limit=1)
                if not attribute_value:
                    attribute_value = self.env['product.attribute.value'].create({
                        'name': row.get('Standard_size/Value'),
                        'attribute_id': attribute.id,
                    })

                product_template_attribute_line = self.env['product.template.attribute.line'].search([
                    ('product_tmpl_id', '=', product_template.id),
                    ('attribute_id', '=', attribute.id),
                ], limit=1)

                if not product_template_attribute_line:
                    product_template_attribute_line = self.env['product.template.attribute.line'].create({
                        'product_tmpl_id': product_template.id,
                        'attribute_id': attribute.id,
                        'value_ids': [(6, 0, [attribute_value.id])],
                    })
                else:
                    if attribute_value not in product_template_attribute_line.value_ids:
                        product_template_attribute_line.write({'value_ids': [(4, attribute_value.id)]})

                product_variant = self.env['product.product'].search([
                    ('product_tmpl_id', '=', product_template.id),
                    ('product_template_attribute_value_ids.product_attribute_value_id', '=', attribute_value.id),
                ], limit=1)

                if not product_variant:
                    product_variant = self.env['product.product'].create({
                        'name': row.get('variant_name'),
                        'product_tmpl_id': product_template.id,
                        'product_template_attribute_value_ids': [(4, attribute_value.id)],
                        'default_code': row.get('Product_name'),
                        'mrp_size': row.get('Manufacturing_Size'),
                        'finishing_size': row.get('Finishing_size'),
                        'shape_size': row.get('Shape'),
                    })
                else:
                    product_variant.write({'default_code': row.get('Product_name')})
                    product_variant.write({'mrp_size': row.get('Manufacturing_Size')})
                    product_variant.write({'finishing_size': row.get('Finishing_size')})
                    product_variant.write({'shape_size': row.get('Shape')})
                buy = row['buy'].lower() == 'true'
                replenish_on_order = row['replenish_on_order'].lower() == 'true'
                manufacture = row['manufacture'].lower() == 'true'
                route_ids = []
                if replenish_on_order:
                    route_ids.append((4, replenish_on_order_route.id))
                else:
                    route_ids.append((3, replenish_on_order_route.id))

                if buy:
                    route_ids.append((4, buy_route.id))
                else:
                    route_ids.append((3, buy_route.id))

                if manufacture:
                    route_ids.append((4, manufacture_route.id))
                else:
                    route_ids.append((3, manufacture_route.id))

                product_template.write({
                    'route_ids': route_ids,
                })
                if manufacture :
                    bom_id = self.env['mrp.bom'].search([
                    ('product_tmpl_id', '=', product_template.id),
                    ('product_id', '=', product_variant.id),
                    ], limit=1)
                    if not bom_id :
                        bom_id = self.env['mrp.bom'].create({
                        'product_tmpl_id':  product_template.id,
                        'product_id':   product_variant.id,
                        'product_qty':   1,
                    })
                    if bom_id:
                        bom_id.product_tmpl_id = product_template.id
                        bom_id.product_id = product_variant.id
                        bom_id.product_qty = 1
                    
            return {'type': 'ir.actions.act_window_close'}
        
        if self.upload == 'bom' :
            for row in reader:              
                component_product_id = self.env['product.product'].search([
                    ('default_code', '=', row.get('component_product')),
                ], limit=1)
                
                product_id = self.env['product.product'].search([
                    ('default_code', '=', row.get('product_variant')),
                ], limit=1)
                product_tmpl_id = self.env['product.template'].search([('name', '=', row.get('product_template'))], limit =1)
              
                bom_id = self.env['mrp.bom'].search([('product_id', '=', product_id.id)], limit=1)
                if bom_id:
                    operation = self._find_or_create_operation(row.get('operation_sequence'), row.get('operation_name'), row.get('work_center'), bom_id)
                    if operation :
                        _logger.info("~~~~~~%r~~~", operation)
                        if component_product_id:
                            bom_line = self.env['mrp.bom.line'].create({
                                'product_id': component_product_id.id,
                                'product_qty' : row.get('quantity'),
                                'operation_id': operation.id,
                                'product_uom_id' : component_product_id.uom_id.id,
                                'bom_id': bom_id.id,
                            })
                            if bom_line :
                                bom_id.bom_line_ids += bom_line

            return {'type': 'ir.actions.act_window_close'}

    def _find_or_create_operation(self, sequence, name, work_center, bom_id):
        work_center_id = self.env['mrp.workcenter'].search([
                    ('name', '=', work_center),
                ], limit=1)
        if work_center_id:
            operation = self.env['mrp.routing.workcenter'].search([('bom_id', '=', bom_id.id), ('name', '=', name), ('workcenter_id', '=', work_center_id.id)], limit=1)
            if not operation:
                operation = self.env['mrp.routing.workcenter'].create({
                    'sequence': sequence,
                    'bom_id' : bom_id.id,
                    'name': name,
                    'workcenter_id': work_center_id.id,
                })
            return operation

    def download_sample_files(self):
        url = ''
        if self._context.get('file') == 'product':
            url = "/innorug_manufacture/static/files/import_products_sample.csv"
        if not url:
            url = "/innorug_manufacture/static/files/products_cosumption_sample_.csv" \
                if self._context.get('file') == 'consumption' \
                else "/innorug_manufacture/static/files/bom_with_routing_sample.csv"
        return {
            'type': 'ir.actions.act_url',
            'url': url
        }
        
