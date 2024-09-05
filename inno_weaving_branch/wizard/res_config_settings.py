from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    inter_warehouse_operation_id = fields.Many2one(string='Inter Warehouse Operation',
                                                   comodel_name='stock.picking.type')
    
    def execute(self):
        res = super().execute()
        for rec in self:
            config_id = self.env['inno.config'].sudo().search([], limit=1)
            if not config_id:
                self.env['inno.config'].sudo().create({
                    'inter_warehouse_operation_id': rec.inter_warehouse_operation_id.id})
            else:
                config_id.sudo().write({'inter_warehouse_operation_id': rec.inter_warehouse_operation_id.
                                       id if rec.inter_warehouse_operation_id else False})
        return res

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        config_id = self.env['inno.config'].sudo().search([], limit=1)
        if config_id:
            res.update({'inter_warehouse_operation_id': config_id.inter_warehouse_operation_id.id})
        return res

