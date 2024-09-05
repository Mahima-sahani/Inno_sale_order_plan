from odoo import fields, models, _, api
from odoo.exceptions import UserError

class MrpWorkOrder(models.Model):
    _inherit = 'mrp.workorder'

    job_work_lines_ids = fields.One2many(comodel_name="mrp.job.work", inverse_name="mrp_work_order_id",
                                         string="Job Work")
    jobwork_allotment_ids = fields.One2many("jobwork.allotment", "work_order_id", string="Branch Wise Allotment")
