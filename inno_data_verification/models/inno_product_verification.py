from odoo import models, fields, _, api
from odoo.exceptions import UserError


class InnoProductVerification(models.Model):
    _name = 'inno.product.verification'
    _description = 'Product Verificaiton'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    product_id = fields.Many2one(comodel_name='product.template', string='Design')
    name = fields.Char(string='Name', related='product_id.name', store=True)
    state = fields.Selection(selection=[('designing', 'Design Team Verification'),
                                        ('manufacturing', 'Manufacturing Team Verification'),
                                        ('admin', 'Admin Verification'), ('verified', 'Product Data Verified')],
                             default='designing', group_expand='_expand_groups')
    bom_id = fields.Many2one(comodel_name='mrp.bom')
    priority = fields.Selection(selection=[('normal', 'Normal'), ('urgent', 'Urgent')])
    color = fields.Integer(compute='compute_kanban_color', default=2)
    division_id = fields.Many2one( compute='_compute_division',store=True)
    weaving = fields.Boolean("Weaving Rate Verified", tracking=True)
    finishing = fields.Boolean("Finishing Rate Verified",tracking=True)

    @api.depends('product_id')
    def _compute_division(self):
        for rec in self:
            if rec.product_id:
                rec.write({'division_id' : rec.product_id.division_id.id})
            else:
                rec.division_id = False


    def compute_kanban_color(self):
        for rec in self:
            rec.color = 2 if rec.priority == 'normal' else 4

    @api.model
    def _expand_groups(self, states, domain, order):
        return ['designing', 'manufacturing', 'admin', 'verified']

    def open_bom(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _(f"BOM of {self.product_id.name}"),
            'view_mode': 'form',
            'res_model': 'mrp.bom',
            'res_id': self.bom_id.id
        }

    def open_design(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _(f"{self.product_id.name}"),
            'view_mode': 'form',
            'res_model': 'product.template',
            'res_id': self.product_id.id
        }

    def open_skus(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _(f"{self.product_id.name}"),
            'view_mode': 'tree,form',
            'res_model': 'product.product',
            'domain': [('id', 'in', self.product_id.product_variant_ids.ids)]
        }

    def do_verify(self):
        if self._context.get('type') == 'design':
            self.message_post(body="<b>Design Verification Done</b>")
            self.state = 'manufacturing'
        if self._context.get('type') == 'manufacturing':
            if not self.weaving or not self.finishing:
                raise UserError(_("Please verify weaving and finishing Rate First."))
            self.message_post(body="<b>Manufacturing Verification Done</b>")
            self.state = 'admin'
            self.message_post(body="<b>Admin Verification Done</b>")
            self.product_id.is_verified = True
            verification_ids = self.env['inno.product.verification'].search([('product_id', '=', self.product_id.id)])
            if verification_ids:
                verification_ids.write({'state': 'verified'
                           })
        if self._context.get('type') == 'admin':
            self.product_id.is_verified = True
            self.message_post(body="<b>Admin Verification Done</b>")
            self.state = 'verified'


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

    def re_sync_materials(self):
        boms = self.product_id.bom_ids.filtered(lambda bom: bom.id != self.bom_id.id)
        design_components = self.bom_id.bom_line_ids
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
        self.message_post(body="<b>Updated Materials</b>")


    def re_sync_operations(self):
        boms = self.product_id.bom_ids.filtered(lambda bom: bom.id != self.bom_id.id)
        design_operations = self.bom_id.operation_ids
        for bom in boms:
            bom.operation_ids.filtered(lambda op: op.workcenter_id.id not in design_operations.workcenter_id.ids).unlink()
            for operation in design_operations:
                existing_operation = bom.operation_ids.filtered(lambda op: op.workcenter_id.id == operation.workcenter_id.id)
                if existing_operation:
                    existing_operation.write({'sequence': operation.sequence})
                else:
                    bom.write({'operation_ids': [(0, 0, {'name': operation.name, 'sequence': operation.sequence,
                                                         'workcenter_id': operation.workcenter_id.id})]})
        self.message_post(body="<b>Updated Operation</b>")

    def add_all_product_to_verification(self):
        all_products = self.env['product.template'].search([('is_raw_material', '=', False)])
        all_verification = self.search([]).product_id.ids
        data_to_create = [{'product_id': product.id, 'priority': 'normal', 'bom_id': self.get_bom_id(product)}
                          for product in all_products if product.id not in all_verification]
        self.env['inno.product.verification'].create(data_to_create[:5000])

    @staticmethod
    def get_bom_id(design):
        return design.bom_ids.filtered(lambda bom: bom.product_tmpl_id and not bom.product_id).id
