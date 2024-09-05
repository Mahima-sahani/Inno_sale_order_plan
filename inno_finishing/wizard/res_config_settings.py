from odoo import models, fields, api,_
from odoo.exceptions import UserError, ValidationError, MissingError


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    full_finishing_id = fields.Many2one(comodel_name="mrp.workcenter", string="Full Finishing")
    without_materials_operation_ids = fields.Many2many(comodel_name="mrp.workcenter",
                                                      string="Without Materials Operation")
    finish_product_ids = fields.Many2many(comodel_name="product.product", relation='finish_product_rel', string="Optional Product")
    finish_opt_product_ids = fields.Many2many(comodel_name="product.product", relation='finish_opt_product_rel',)
    binding_id = fields.Many2one(comodel_name="mrp.workcenter", string="Binding")
    gachhai_id = fields.Many2one(comodel_name="mrp.workcenter", string="Gachhai")
    finishing_journal_id = fields.Many2one(comodel_name='account.journal', string='Weaving Journal')
    letexing_id = fields.Many2one(comodel_name="mrp.workcenter", string="Letexing")
    washing_id = fields.Many2one(comodel_name="mrp.workcenter", string="Washing")



    def execute(self):
        res = super().execute()
        for rec in self:
            config_id = self.env['inno.config'].sudo().search([], limit=1)
            if not config_id:
                self.env['inno.config'].sudo().create({
                    'full_finishing_id': rec.full_finishing_id.id if rec.full_finishing_id else False,
                    'binding_id': rec.binding_id.id if rec.binding_id else False,
                    'gachhai_id': rec.gachhai_id.id if rec.gachhai_id else False,
                    'letexing_id': rec.letexing_id.id if rec.letexing_id else False,
                    'washing_id': rec.washing_id.id if rec.washing_id else False,
                    'finish_product_ids': [(6,0,rec.finish_product_ids.ids)],
                    'finish_opt_product_ids': [(6,0,rec.finish_opt_product_ids.ids)],
                    'without_materials_operation_ids': [(6,0,rec.without_materials_operation_ids.ids )],
                    'finishing_journal_id': rec.full_finishing_id.id
                })

            else:
                config_id.sudo().write({
                    'full_finishing_id': rec.full_finishing_id.id if rec.full_finishing_id else False,
                    'binding_id': rec.binding_id.id if rec.binding_id else False,
                    'gachhai_id': rec.gachhai_id.id if rec.gachhai_id else False,
                    'letexing_id': rec.letexing_id.id if rec.letexing_id else False,
                    'washing_id': rec.washing_id.id if rec.washing_id else False,
                    'finish_product_ids':[(6,0,rec.finish_product_ids.ids)],
                    'finish_opt_product_ids':[(6,0,rec.finish_opt_product_ids.ids)],
                  'without_materials_operation_ids': [(6,0, rec.without_materials_operation_ids.ids)],
                'finishing_journal_id': rec.finishing_journal_id.id})
        return res

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        config_id = self.env['inno.config'].sudo().search([], limit=1)
        if config_id:
            res.update({'finish_opt_product_ids': [(6,0,config_id.finish_opt_product_ids.ids)],
                        'full_finishing_id': config_id.full_finishing_id.id,
                        'binding_id': config_id.binding_id.id,
                        'gachhai_id': config_id.gachhai_id.id,
                        'letexing_id': config_id.letexing_id.id,
                        'washing_id': config_id.washing_id.id,
                        'finish_product_ids': [(6,0,config_id.finish_product_ids.ids)],
                        'without_materials_operation_ids': [(6,0,config_id.without_materials_operation_ids.ids)],
                        'finishing_journal_id': config_id.finishing_journal_id.id
                        })
        return res
