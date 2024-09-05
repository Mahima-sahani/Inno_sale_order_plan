from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, MissingError


class VendorBomWizard(models.TransientModel):
    _name = 'vendor.bom.wizard'

    def get_purchase_domain(self):
        purchases = self.env['inno.purchase'].sudo().search(
            [('state', 'in', ['1_draft', 'purchase']), ('types', 'in',
                                                        ['tufting_cloth_weaving', 'newar_production', 'tana_job_order',
                                                         'third_backing_cloth', 'spinning'])])
        domain = [
            ('id', 'in', purchases.ids)]
        return domain

    inno_purchase_id = fields.Many2one("inno.purchase", string="Order No", domain=get_purchase_domain)
    subcontractor_id = fields.Many2one(related="inno_purchase_id.subcontractor_id", comodel_name='res.partner',
                                       string="Vendor")
    bom_wizard_line = fields.One2many("vendor.bom.wizard.line", 'bom_wizard_id')
    total_qty = fields.Float("Total Qty", digits=(12, 4), compute='_compute_total_area')
    unit = fields.Char("Units")

    @api.onchange('inno_purchase_id', 'total_qty')
    def get_details_of_bom(self):
        for rec in self:
            if rec.inno_purchase_id and rec.total_qty > 0.00:
                # bom_line_ids
                for prod in rec.inno_purchase_id.inno_purchase_line.product_id:
                    if len(prod.bom_line_ids) == 2:
                        boms = prod.bom_ids.filtered(lambda bl: bl.product_id)
                    if len(prod.bom_ids) == 1:
                        boms = prod.bom_ids[0]
                        rec.create_material_line(boms)
                    else:
                        if prod.bom_ids:
                            boms = prod.bom_ids.filtered(lambda bl: bl.product_id)
                            rec.create_material_line(boms)

    def create_material_line(self, boms):
        for rec in boms.bom_line_ids:
            line = self.bom_wizard_line.filtered(lambda bw: rec.product_id.id in bw.product_id.ids)
            if line:
                line.product_qty += rec.product_qty
            else:
                line = [(0, 0, {'product_id': rec.product_id.id, 'product_qty': rec.product_qty})]
                self.write({'bom_wizard_line': line})

    @api.depends('inno_purchase_id', 'subcontractor_id', )
    def _compute_total_area(self):
        for rec in self:
            total_area = sum(rec.inno_purchase_id.inno_purchase_line.mapped('deal_qty')) or 0
            rec.total_qty = 0.0
            if total_area > 0.000 and rec.inno_purchase_id.types in ['tufting_cloth_weaving', 'third_backing_cloth']:
                rec.write({'total_qty': sum(rec.inno_purchase_id.inno_purchase_line.mapped('deal_qty')) or 0,
                           'unit': rec.inno_purchase_id.inno_purchase_line[0].deal_uom_id.name})
            else:
                rec.write({'total_qty': sum(rec.inno_purchase_id.inno_purchase_line.mapped('product_qty')) or 0,
                           'unit': rec.inno_purchase_id.inno_purchase_line[0].uom_id.name if rec.inno_purchase_id.inno_purchase_line.uom_id else ''})

    def button_confirm(self):

        line = [(0, 0, {'product_id': component.product_id.id, 'quantity': component.product_qty,
                        'location_id': component.location_id.id,
                        'remark': component.remark}) for component in self.bom_wizard_line]
        if line:
            material_id = self.env['inno.vendor.material'].create({'partner_id': self.subcontractor_id.id,
                                                                   'inno_purchase_id': self.inno_purchase_id.id,
                                                                   'state': 'draft',
                                                                   'vendor_materials_line_ids': line,
                                                                   'name': self.env['ir.sequence'].next_by_code(
                                                                       'po_vd_mt_seq', )})
            if material_id:
                action = {
                    'name': _('Material Issue'),
                    'view_mode': 'form',
                    'res_model': 'inno.vendor.material',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form', 'res_id': material_id.id
                }
                return action

    # def button_confirm(self):
    #     pick_id = False
    #     for component in self.bom_wizard_line:
    #         lines = self.finishing_work_id.material_lines.filtered(
    #             lambda ml: component.product_id.id in ml.product_id.ids)
    #         if not lines:
    #             self.finishing_work_id.write({'material_lines': [(0, 0, {
    #                 'product_id': component.product_id.id,
    #                 'product_qty': component.product_qty,
    #                 'qty_previous': self.get_update_date_qty_previous(component),
    #                 'location_id': component.location_id.id,
    #                 'extra': component.extra,
    #                 'remark': component.remark,
    #                 'rate': component.rate,
    #                 'finishing_work_id': self.finishing_work_id.id
    #             })], 'material_state': True})
    #         else:
    #             lines.qty_amended += component.product_qty
    #     if self.bom_wizard_line and self.finishing_work_id.jobwork_barcode_lines:
    #         ml_lines = self.bom_wizard_line.filtered(lambda ml: 0.0 < ml.product_qty - ml.qty_previous)
    #         if ml_lines:
    #             for rec in ml_lines.location_id:
    #                 lines = ml_lines.filtered(lambda id: id.location_id.id == rec.id)
    #                 dest_location = self.env['stock.location'].search([('usage', '=', 'supplier')], limit=1).id
    #                 try:
    #                     job_stock_move = self.finishing_work_id.prepare_job_stock_move(rec.id, dest_location, lines)
    #                     if self.finishing_work_id.is_external == True:
    #                         operation_type = rec.warehouse_id.out_type_id
    #                         pick_id = self.finishing_work_id.create_picking(job_stock_move, operation_type, rec.id,
    #                                                                         dest_location)
    #                     else:
    #                         operation_type_in = rec.warehouse_id.int_type_id
    #                         pick_id = self.finishing_work_id.create_picking(job_stock_move, operation_type_in, rec.id,
    #                                                                         dest_location)
    #                 except Exception as ex:
    #                     raise UserError(_(ex))
    #         else:
    #             raise UserError(_("Material already available with subcontractor"))
    #     else:
    #         raise UserError(_("Already materials issue or no barcodes or Products not allocated to subcontractor"))
    #     if pick_id:
    #         action = {
    #             'name': _('Delivery'),
    #             'view_mode': 'form',
    #             'res_model': 'stock.picking',
    #             'type': 'ir.actions.act_window',
    #             'view_type': 'form', 'res_id': pick_id.id
    #         }
    #         return action

    def get_update_date_qty_previous(self, component):
        if component.qty_previous > 0.0:
            component.material_line_id.quantity = component.material_line_id.quantity - component.qty_previous
            return component.qty_previous
        return 0.0


class VendorBomWizardLine(models.TransientModel):
    _name = 'vendor.bom.wizard.line'

    bom_wizard_id = fields.Many2one(comodel_name="vendor.bom.wizard", )
    product_id = fields.Many2one(comodel_name="product.product", string="Components")
    product_qty = fields.Float("Quantity", digits=(12, 4))
    uom_id = fields.Many2one(related="product_id.uom_id", string="Units", )
    location_id = fields.Many2one("stock.location", string="Location",
                                  default=lambda self: self.env.user.material_location_id.id,
                                  domain=[('usage', '=', 'internal')])
    remark = fields.Text("Remarks")
    in_hand = fields.Float(compute='get_onhand_qty')
    released_qty = fields.Float(compute='get_released_qty')

    @api.depends('product_id', )
    def get_released_qty(self):
        for rec in self:
            vendor_materials = self.env['inno.vendor.material'].sudo().search(
                [('inno_purchase_id', '=', rec.bom_wizard_id.inno_purchase_id.id)])
            lines = vendor_materials.vendor_materials_line_ids.filtered(
                lambda vml: rec.product_id.id in vml.product_id.ids)
            rec.write({'released_qty': 0.00})
            if lines:
                qty = sum([mat.quantity for mat in lines])
                rec.write({'released_qty': qty})

    @api.depends('product_id', 'location_id')
    def get_onhand_qty(self):
        for rec in self:
            materials = self.env['stock.quant'].sudo().search(
                [('location_id', '=', rec.env.user.material_location_id.id), ('product_id', '=', rec.product_id.id)])
            rec.write({'in_hand': 0.00})
            if materials:
                qty = sum([mat.quantity for mat in materials])
                rec.write({'in_hand': qty})

    # @api.onchange('product_id')
    # def get_details_of_bom(self):
    #     for rec in self:
    #         if rec.product_id:
    #             bom_lines = rec.bom_wizard_id.finishing_work_id.jobwork_barcode_lines.barcode_id.division_id.finishing_bom_lines.filtered(
    #                 lambda
    #                     bom: bom.work_center_id.id == rec.bom_wizard_id.finishing_work_id.operation_id.id and rec.product_id.id in bom.product_id.ids)
    #             if bom_lines:
    #                 rec.write({'rate': bom_lines.rate, 'extra': bom_lines.extra,
    #                             'product_qty': bom_lines.product_qty * rec.bom_wizard_id.total_area})
    #
    # def update_reserved_material(self):
    #     pending_material_id = self.env['inno.pending.material'].sudo().search(
    #         [('subcontractor_id', '=', self.bom_wizard_id.subcontractor_id.id),
    #          ('process', '=', 'finishing')], limit=1)
    #     if pending_material_id:
    #         pending_material_lines = pending_material_id.material_line_ids.filtered(
    #             lambda pr: self.product_id.id in pr.product_id.ids)
    #         if pending_material_lines:
    #             self.qty_previous += pending_material_lines.quantity
    #             self.write({'material_line_id': pending_material_lines.id})
