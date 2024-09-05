from odoo import models, fields


class InnoConfig(models.Model):
    _inherit = 'inno.config'

    dyeing_journal_id = fields.Many2one(comodel_name='account.journal', string='Dyeing Journal')
