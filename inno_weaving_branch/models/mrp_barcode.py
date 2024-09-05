from odoo import models, fields, api


class MrpBarcode(models.Model):
    _inherit = 'mrp.barcode'

    branch_main_job_work_id = fields.Many2one(string='Branch Main Job Work', comodel_name='main.jobwork', tracking=True)
    branch_id = fields.Many2one(comodel_name="weaving.branch")
