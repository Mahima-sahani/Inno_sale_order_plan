from odoo import models, fields, _,api
import logging
_logger = logging.getLogger(__name__)


class InnoRawMaterials(models.Model):
    _name = 'raw.material'
    _description = 'Raw Materials'

    name = fields.Char("Raw Material")
    material_id = fields.Many2one('product.template', string="Material ID")
    raw_status = fields.Selection(selection=[('mapped', 'Mapped'), ('Unmapped', 'Unmapped')], string="Mapped Status")
    material_lines = fields.One2many(comodel_name="raw.material.line", inverse_name="raw_material_id", string="Attribute")
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
                   ('woolen_febric', 'WOOLEN FEBRIC'), ('cotton_cone', 'COTTON CONE'),
                   ('cotton','COTTON')],
        string="Raw Material Group")
    uom_id = fields.Many2one("uom.uom")
    line_counts = fields.Integer("Lines",compute='compute_len', store=True)

    @api.depends('material_lines')
    def compute_len(self):
        for rec in self:
            line = len(rec.material_lines)
            rec.line_counts = line or 0

    def mapped_process_raw_materials(self):
        count = 0
        for rec in self:
            try:
                if rec.raw_status == 'Unmapped':
                    if rec.material_id:
                        is_done = rec.create_varient(rec)
                        if is_done:
                            self._cr.commit()
                    else:
                        material_id = self.env['product.template'].search([('name', '=', rec.name)], limit=1)
                        if not material_id:
                            replenish_on_order_route = self.env['stock.route'].search(
                                [('name', '=', 'Replenish on Order (MTO)')], limit=1)
                            buy_route = self.env['stock.route'].search([('name', '=', 'Buy')], limit=1)
                            materials = {'name': rec.name,'uom_id': rec.uom_id.id, 'uom_po_id': rec.uom_id.id,
                                              # 'route_ids': [(4, replenish_on_order_route.id), (4, buy_route.id), ],
                                              'sale_ok': True, 'purchase_ok': True, 'is_raw_material': True,
                                              'detailed_type': 'product', 'invoice_policy': 'delivery',
                                              'raw_material_group': rec.raw_material_group
                                              }
                            rec.material_id = self.env['product.template'].create(materials)
                            if not rec.material_lines:
                                rec.raw_status = 'mapped'
                        elif material_id:
                            rec.material_id = material_id.id
                        if rec.material_lines:
                           is_done = rec.create_varient(rec)
                           if is_done:
                               self._cr.commit()
            except Exception as ex:
                # self.create_logs('Failed', 'failed', message=ex)
                continue
            count += 1
            _logger.info("count...line............ %r  ", count)
            if count % 20 == 0:
                self._cr.commit()

    def create_varient(self,rec):
        materials_to_map =rec.material_lines.filtered(lambda ml: not ml.sku_id)[:1000]
        if rec:
            if not rec.material_id.attribute_line_ids:
                rec.material_id.update({
                    'attribute_line_ids': [
                        (0, 0, {'attribute_id': rec.material_lines.mapped('shade_id').id,
                                'value_ids': [
                                    (4, att.attribute_value.id) for att in materials_to_map]})]})
            else:
                rec.material_id.attribute_line_ids.filtered(
                    lambda al: al.attribute_id.id == rec.material_lines.mapped('shade_id').id).write({'value_ids':
                    [(4, att.attribute_value.id) for att in materials_to_map]})
            if len(rec.material_lines) == len(rec.material_id.product_variant_ids):
                rec.raw_status = 'mapped'
            else:
                for line in materials_to_map:
                    line.sku_id = rec.material_id.product_variant_ids.filtered(
                        lambda pv: line.attribute_value.name in pv.product_template_attribute_value_ids.mapped('name')).id
            return True
        return False


class InnoRawMaterialsLine(models.Model):
    _name = 'raw.material.line'

    shade = fields.Char("Shade")
    attribute = fields.Char("Attribute")
    shade_id = fields.Many2one("product.attribute", string="Attribute Shade")
    attribute_value = fields.Many2one('product.attribute.value', string="Value")
    sku_id = fields.Many2one("product.product", string="Material SKU")
    raw_material_id = fields.Many2one(comodel_name="raw.material", string="Materials")
