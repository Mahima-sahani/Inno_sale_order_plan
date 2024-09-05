from odoo import models, fields, api


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    dyeing_journal_id = fields.Many2one(comodel_name='account.journal', string='Dyeing Journal')

    def execute(self):
        res = super().execute()
        for rec in self:
            config_id = self.env['inno.config'].sudo().search([], limit=1)
            if not config_id:
                self.env['inno.config'].sudo().create({
                    'dyeing_journal_id': rec.dyeing_journal_id.id
                })
            else:
                config_id.sudo().write({
                    'dyeing_journal_id': rec.dyeing_journal_id.id
                })
        return res

    @api.model
    def default_get(self, fields):
        res = super().default_get(fields)
        config_id = self.env['inno.config'].sudo().search([], limit=1)
        if config_id:
            res.update({
                'dyeing_journal_id': config_id.dyeing_journal_id.id
            })
        return res