from odoo import models, fields


class InnoConfig(models.Model):
    _inherit = 'inno.config'

    weaving_operation_id = fields.Many2one(comodel_name='mrp.workcenter')
    main_warehouse_id = fields.Many2one(comodel_name='stock.warehouse')
    extra_time = fields.Integer()
    barcode_reprint_penalty = fields.Integer()
    allowed_fragments = fields.Integer()
    fragment_penalty = fields.Float()
    penalty_product_id = fields.Many2one(comodel_name='product.product')
    incentive_product_id = fields.Many2one(comodel_name='product.product')
    time_incentive = fields.Float()
    manager_time_incentive = fields.Float()
    weaving_journal_id = fields.Many2one(comodel_name='account.journal', string='Weaving Journal')
