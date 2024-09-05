from odoo import models, fields


class HrJob(models.Model):
    _inherit = 'hr.job'

    def name_get(self):
        res = []
        for job in self:
            name = f"{job.name} ({job.department_id.name})"
            res.append((job.id, name))
        return res
