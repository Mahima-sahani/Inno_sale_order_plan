from odoo import models, fields


class MrpJobWork(models.Model):
    _inherit = 'mrp.job.work'

    allotment_id = fields.Many2one(comodel_name='jobwork.allotment')

