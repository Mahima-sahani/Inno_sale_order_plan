from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    purchase_journal_id = fields.Many2one(comodel_name='account.journal', string='Purchase Journal')

    def execute(self):
        res = super().execute()
        for rec in self:
            config_id = self.env['inno.config'].sudo().search([], limit=1)
            if not config_id:
                self.env['inno.config'].sudo().create({
                    'purchase_journal_id': rec.purchase_journal_id.id
                })
            else:
                config_id.sudo().write({
                    'purchase_journal_id': rec.purchase_journal_id.id
                })
        return res

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        config_id = self.env['inno.config'].sudo().search([], limit=1)
        if config_id:
            res.update({
                'purchase_journal_id': config_id.purchase_journal_id.id
            })
        return res