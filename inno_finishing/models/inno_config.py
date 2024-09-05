from odoo import models, fields


class InnoConfig(models.Model):
    _inherit = 'inno.config'

    full_finishing_id = fields.Many2one(comodel_name ="mrp.workcenter", string="Full Finishing")
    without_materials_operation_ids = fields.Many2many(comodel_name="mrp.workcenter", string="Without Materials Operation")

    finish_product_ids = fields.Many2many(comodel_name="product.product", relation='inno_finish_product_rel',
                                          string="Optional Product")
    finish_opt_product_ids = fields.Many2many(comodel_name="product.product", relation='inno_finish_opt_product_rel', )
    binding_id = fields.Many2one(comodel_name="mrp.workcenter", string="Binding")
    gachhai_id = fields.Many2one(comodel_name="mrp.workcenter", string="Gachhai")
    finishing_journal_id = fields.Many2one(comodel_name='account.journal', string='Weaving Journal')
    letexing_id = fields.Many2one(comodel_name="mrp.workcenter", string="Letexing")
    washing_id = fields.Many2one(comodel_name="mrp.workcenter", string="Washing")

