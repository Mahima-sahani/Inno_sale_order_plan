import datetime
from odoo import models, api


class ReportMaterialIssue(models.AbstractModel):
    _name = 'report.inno_finishing.report_print_bazaar_finishing_receiving'
    _description = 'Will Provide the report of all the received Barcodes'

    @api.model
    def _get_report_values(self, docids, data=None):
        records = self.env['mrp.barcode'].sudo().browse(docids)
        data = {'division': self.env.user.division_id.name}
        sub_data = {}
        subcontractors = records.sudo().finishing_jobwork_id.subcontractor_id
        for subcontractor in subcontractors:
            sub_data.update({subcontractor.id: {
                'subcontractor_name': subcontractor.name, 'jobwork': [
                    {'jobwork_name': job.name, 'barcodes': ', '.join(records.filtered(
                        lambda bcode: bcode.sudo().finishing_jobwork_id.id == job.id).mapped('name'))} for job in
                    records.sudo().finishing_jobwork_id.filtered(lambda mj: mj.subcontractor_id.id == subcontractor.id)]}})
        if sub_data:
            data.update({'sub_data': sub_data})
        return {
            'doc_ids': docids,
            'doc_model': 'mrp.barcode',
            'docs': records,
            'data': data}