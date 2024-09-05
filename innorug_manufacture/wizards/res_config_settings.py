from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    weaving_operation_id = fields.Many2one(comodel_name='mrp.workcenter')
    main_warehouse_id = fields.Many2one(comodel_name='stock.warehouse')
    penalty_product_id = fields.Many2one(comodel_name='product.product')
    incentive_product_id = fields.Many2one(comodel_name='product.product')
    extra_time = fields.Integer()
    barcode_reprint_penalty = fields.Integer()
    allowed_fragments = fields.Integer()
    fragment_penalty = fields.Float()
    time_incentive = fields.Float()
    manager_time_incentive = fields.Float()
    weaving_journal_id = fields.Many2one(comodel_name='account.journal', string='Weaving Journal')


    def execute(self):
        res = super().execute()
        for rec in self:
            workcenter_obj = self.env['mrp.workcenter']
            workcenter_obj.sudo().search([]).write({'is_weaving_workcenter': False})
            workcenter = workcenter_obj.browse(rec.weaving_operation_id.id if rec.weaving_operation_id else False)
            workcenter.sudo().is_weaving_workcenter = True
            config_id = self.env['inno.config'].sudo().search([], limit=1)
            if not config_id:
                self.env['inno.config'].sudo().create({
                    'extra_time': rec.extra_time or 0,
                    'weaving_operation_id': rec.weaving_operation_id.id if rec.weaving_operation_id else False,
                    'main_warehouse_id': rec.main_warehouse_id.id if rec.main_warehouse_id else False,
                    'barcode_reprint_penalty': rec.barcode_reprint_penalty,
                    'allowed_fragments': rec.allowed_fragments, 'fragment_penalty': rec.fragment_penalty,
                    'penalty_product_id': rec.penalty_product_id.id if rec.penalty_product_id else False,
                    'incentive_product_id': rec.incentive_product_id.id if rec.incentive_product_id else False,
                    'time_incentive': rec.time_incentive, 'manager_time_incentive': rec.manager_time_incentive,
                    'weaving_journal_id': rec.weaving_journal_id.id
                })
            else:
                config_id.sudo().write({
                    'extra_time': rec.extra_time or 0,
                    'weaving_operation_id': rec.weaving_operation_id.id if rec.weaving_operation_id else False,
                    'main_warehouse_id': rec.main_warehouse_id.id if rec. main_warehouse_id else False,
                    'barcode_reprint_penalty': rec.barcode_reprint_penalty,
                    'allowed_fragments': rec.allowed_fragments, 'fragment_penalty': rec.fragment_penalty,
                    'penalty_product_id': rec.penalty_product_id.id if rec.penalty_product_id else False,
                    'incentive_product_id': rec.incentive_product_id.id if rec.incentive_product_id else False,
                    'time_incentive': rec.time_incentive, 'manager_time_incentive': rec.manager_time_incentive,
                    'weaving_journal_id': rec.weaving_journal_id.id
                })
        return res

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        config_id = self.env['inno.config'].sudo().search([], limit=1)
        if config_id:
            res.update({
                'extra_time': config_id.extra_time or 0,
                'weaving_operation_id': config_id.weaving_operation_id.id,
                'main_warehouse_id': config_id.main_warehouse_id.id,
                'barcode_reprint_penalty': config_id.barcode_reprint_penalty,
                'allowed_fragments': config_id.allowed_fragments, 'fragment_penalty': config_id.fragment_penalty,
                'penalty_product_id': config_id.penalty_product_id.id,
                'incentive_product_id': config_id.incentive_product_id.id,
                'time_incentive': config_id.time_incentive, 'manager_time_incentive': config_id.manager_time_incentive,
                'weaving_journal_id': config_id.weaving_journal_id.id
            })
        return res

