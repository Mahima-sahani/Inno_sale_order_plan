from odoo import models,fields


class ReportWizad(models.TransientModel):
    _inherit = 'inno.weaving.reports'

    branch_id = fields.Many2one("weaving.branch", string="Branch")