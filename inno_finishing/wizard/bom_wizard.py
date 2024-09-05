from odoo import models, fields, api,_
from odoo.exceptions import UserError, ValidationError, MissingError


class FinishingBomWizard(models.TransientModel):
    _name = 'finishing.bom.wizard'

    finishing_work_id = fields.Many2one(comodel_name="finishing.work.order", string="Finishing")
    subcontractor_id = fields.Many2one(related="finishing_work_id.subcontractor_id", comodel_name='res.partner',
                                       string="Vendor")
    bom_wizard_line = fields.One2many("finishing.bom.wizard.line", 'bom_wizard_id')
    total_area = fields.Float("Total Area", digits=(12, 4), compute='_compute_total_area')

    @api.depends('finishing_work_id', 'subcontractor_id', )
    def _compute_total_area(self):
        for rec in self:
            total_area = sum(rec.finishing_work_id.jobwork_barcode_lines.mapped('total_area')) or 0
            rec.total_area = 0.0
            if total_area > 0.000:
                rec.write({'total_area': total_area})

    @api.model
    def default_get(self, fields_list):
        rec = super().default_get(fields_list)
        work_order = self.env['finishing.work.order'].browse(self._context.get('active_id'))
        if work_order:
            rec.update({'finishing_work_id': work_order.id,})
        return rec

    def button_confirm(self):
        pick_id = False
        for component in self.bom_wizard_line:
            lines = self.finishing_work_id.material_lines.filtered(lambda ml: component.product_id.id in ml.product_id.ids)
            if not lines:
                self.finishing_work_id.write({'material_lines': [(0, 0, {
                    'product_id': component.product_id.id,
                    'product_qty': component.product_qty,
                    'qty_previous':self.get_update_date_qty_previous(component),
                    'location_id' : component.location_id.id,
                    'extra': component.extra,
                    'remark': component.remark,
                    'rate': component.rate,
                    'finishing_work_id': self.finishing_work_id.id
                })],'material_state' : True})
            else:
                lines.qty_amended += component.product_qty
        if self.bom_wizard_line and self.finishing_work_id.jobwork_barcode_lines:
            ml_lines = self.bom_wizard_line.filtered(lambda ml: 0.0 < ml.product_qty - ml.qty_previous)
            if ml_lines:
                for rec in ml_lines.location_id:
                    lines = ml_lines.filtered(lambda id: id.location_id.id == rec.id)
                    dest_location = self.env['stock.location'].search([('usage', '=', 'supplier')], limit=1).id
                    try:
                        job_stock_move = self.finishing_work_id.prepare_job_stock_move(rec.id, dest_location, lines)
                        if self.finishing_work_id.is_external == True:
                            operation_type = rec.warehouse_id.out_type_id
                            pick_id=self.finishing_work_id.create_picking(job_stock_move, operation_type, rec.id, dest_location)
                        else:
                            operation_type_in = rec.warehouse_id.int_type_id
                            pick_id=self.finishing_work_id.create_picking(job_stock_move, operation_type_in, rec.id, dest_location)
                    except Exception as ex:
                        raise UserError(_(ex))
            else:
                raise UserError(_("Material already available with subcontractor"))
        else:
            raise UserError(_("Already materials issue or no barcodes or Products not allocated to subcontractor"))
        if pick_id:
            action = {
                'name': _('Delivery'),
                'view_mode': 'form',
                'res_model': 'stock.picking',
                'type': 'ir.actions.act_window',
                'view_type': 'form', 'res_id': pick_id.id
            }
            return action

    def get_update_date_qty_previous(self,component):
        if component.qty_previous > 0.0:
            component.material_line_id.quantity =  component.material_line_id.quantity - component.qty_previous
            return component.qty_previous
        return 0.0




class FinishingBomWizardLine(models.TransientModel):
    _name = 'finishing.bom.wizard.line'

    bom_wizard_id = fields.Many2one(comodel_name="finishing.bom.wizard", )
    product_id = fields.Many2one(comodel_name="product.product", string="Components")
    product_qty = fields.Float("Quantity", digits=(12, 4))
    uom_id = fields.Many2one(related="product_id.uom_id", string="Units", )
    location_id = fields.Many2one("stock.location", string="Location",
                                  default=lambda self: self.env.user.material_location_id.id,
                                  domain=[('usage', '=', 'internal')])
    bom_line_id = fields.Many2one(comodel_name="finishing.bom.line", )
    remark = fields.Text("Remarks")
    qty_previous = fields.Float("Previous", digits=(12, 4))
    material_line_id = fields.Many2one(comodel_name="inno.pending.material.line", )
    rate = fields.Float(string="Rate", digits=(4, 2))
    extra = fields.Boolean("If Extra")

    @api.onchange('product_id')
    def get_details_of_bom(self):
        for rec in self:
            if rec.product_id:
                bom_lines = rec.bom_wizard_id.finishing_work_id.jobwork_barcode_lines.barcode_id.division_id.finishing_bom_lines.filtered(
                    lambda
                        bom: bom.work_center_id.id == rec.bom_wizard_id.finishing_work_id.operation_id.id and rec.product_id.id in bom.product_id.ids)
                if bom_lines:
                    rec.write({'rate': bom_lines.rate, 'extra': bom_lines.extra,
                                'product_qty': bom_lines.product_qty * rec.bom_wizard_id.total_area})

    def update_reserved_material(self):
        pending_material_id = self.env['inno.pending.material'].sudo().search(
            [('subcontractor_id', '=', self.bom_wizard_id.subcontractor_id.id),
             ('process', '=', 'finishing')], limit=1)
        if pending_material_id:
            pending_material_lines = pending_material_id.material_line_ids.filtered(
                lambda pr: self.product_id.id in pr.product_id.ids)
            if pending_material_lines:
                self.qty_previous += pending_material_lines.quantity
                self.write({'material_line_id': pending_material_lines.id})
