from odoo import models, fields, api, _
from odoo.exceptions import UserError


class DesignCopy(models.TransientModel):
    _name = 'inno.design.copy'

    inno_research_id = fields.Many2one('inno.research', string="Research Design Number")
    design_id = fields.Many2one('product.template', string="Parent Design", domain="[('division_id', '!=', False)]", )
    new_design = fields.Char(string="New Design")
    is_bom = fields.Boolean("With Bom")


    @api.onchange('new_design')
    def check_new_design(self):
        product_id = self.env['product.template'].search([('name', '=', self.new_design)])
        if product_id:
            raise UserError("The design has already been created.")

    def confirm(self):
        if self.design_id and self.new_design:
            inno_id = self.env['inno.research'].search([('name', '=', self.new_design)])
            product_id = self.env['product.template'].search([('name', '=', self.new_design)])
            if not inno_id and not product_id:
                design_data = {'name': self.new_design, 'state': '1_draft', 'is_active_mrp': True,
                               'construction': self.design_id.construction.id,
                               'collection': self.design_id.collection.id, 'quality': self.design_id.quality.id,
                               'quality_weight': self.design_id.quality.weight,
                               'color_ways': self.design_id.color_ways.id, 'style': self.design_id.style.id,
                               'color': self.design_id.color.id, 'pattern': self.design_id.pattern.id,
                               'contect': self.design_id.contect.id, 'face_content': self.design_id.face_content.id,
                               'remark': self.design_id.remark, 'standard_cost': self.design_id.standard_cost,
                               'origin': self.design_id.origin.id, 'finish_weight': self.design_id.finish_weight,
                               'hns_code': self.design_id.l10n_in_hsn_code,
                               'division_id': self.design_id.division_id.id,
                               'trace': self.design_id.trace, 'map': self.design_id.map,
                               'binding_prm': self.design_id.binding_prm, 'gachhai_prm': self.design_id.gachhai_prm,
                               'durry_prm': self.design_id.durry_prm,
                               'pile_height': self.design_id.pile_height, 'loop_cut': self.design_id.loop_cut}
                design_id = self.env['inno.research'].create(design_data)
                design_id.write({
                    'research_lines': [
                        (0, 0, {'shape': rec.shape_type,
                                'standard_size': self.env['inno.size'].search(
                                    [('name', '=', rec.product_template_attribute_value_ids.mapped('name')[0])]).id,
                                'manufacturing_size': rec.inno_mrp_size_id.id,
                                'finishing_size': rec.inno_finishing_size_id.id}) for rec in
                        self.design_id.product_variant_ids]})
                for rec in design_id.research_lines:
                    rec._compute_product()
                design_id.button_action_confirm()
                if self.design_id.bom_ids:
                    # design_id.button_action_set_operation_and_bom()
                    bom_id = self.env['mrp.bom'].create(
                        {'product_tmpl_id': design_id.product_tmpl_id.id, 'product_qty': 1,
                         'research_id': design_id.id})
                    design_id.write({'bom_id': bom_id.id})
                    design_id.write({
                        'rnd_route_lines': [
                            (0, 0, {'name': rec.name,
                                    'rnd_bom_id': bom_id.id,
                                    'bom_id': bom_id.id,
                                    'workcenter_id': rec.workcenter_id.id}) for rec in
                            self.design_id.bom_ids[0].operation_ids]})
                    if self.is_bom:
                        bom_id.write({
                            'bom_line_ids': [
                                (0, 0, {'product_id': rec.product_id.id,
                                        'product_qty': rec.product_qty,
                                        'research_id': design_id.id,
                                        'operation_id': bom_id.operation_ids[0].id}) for rec in
                                self.design_id.bom_ids.filtered(lambda rc: not rc.product_id.id).bom_line_ids]})
                        design_id.re_sync_materials()
                        design_id.re_sync_operations()
                        design_id.button_add_bom_verified()
                        design_id.state = '2_consumption_mrp'
                    else:
                        design_id.re_sync_materials()
                        design_id.re_sync_operations()
                        design_id.state = '2_consumption_mrp'
                    return {
                        'type': 'ir.actions.act_window',
                        'name': _("Manufacturing"),
                        'view_mode': 'form',
                        # 'view_id': self.env.ref('inno_R_and_D.view_mrp_wizard_order_manufacturing_form').id,
                        'res_model': 'inno.research',
                        'res_id': design_id.id,
                        "target": "current",
                    }
                else:
                    raise UserError("Bom not found")
