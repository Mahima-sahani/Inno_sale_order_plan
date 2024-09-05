from odoo import models, api


class ReportDyeingPlan(models.AbstractModel):
    _name = 'report.inno_sale_order_plan.report_dyeing_plan'
    _description = 'Dyeing Plan'

    @api.model
    def _get_report_values(self, docids, data=None):
        company = self.env['res.company'].search([], limit=1)
        return {'doc_ids': docids, 'doc_model': 'main.jobwork', 'data': data, 'company': company}