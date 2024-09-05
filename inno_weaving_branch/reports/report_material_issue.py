import datetime
from odoo import models, api


class ReportMaterialIssue(models.AbstractModel):
    _inherit = 'report.innorug_manufacture.report_print_material_allocation'

    @api.model
    def _get_report_values(self, docids, data=None):
        res = super()._get_report_values(docids, data)
        record = res.get('docs')
        if record.branch_id:
            res.get('data').update({'site': record.branch_id.name})
        return res
