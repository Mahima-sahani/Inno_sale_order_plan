import datetime
from odoo import models, api


class ReportMaterialIssue(models.AbstractModel):
    _name = 'report.innorug_manufacture.report_print_bazaar_receiving'
    _description = 'Will Provide the report of all the received Barcodes'

    @api.model
    def _get_report_values(self, docids, data=None):
        records = self.env['mrp.barcode'].browse(docids)
        data = {'division': self.env.user.division_id.name}
        sub_data = {}
        subcontractors = records.sudo().main_job_work_id.subcontractor_id
        for subcontractor in subcontractors:
            sub_data.update({subcontractor.id: {
                'subcontractor_name': subcontractor.name, 'jobwork': [
                    {'jobwork_name': job.reference, 'barcodes': ', '.join(records.filtered(
                        lambda bcode: bcode.sudo().main_job_work_id.id == job.id).mapped('name'))} for job in
                    records.sudo().main_job_work_id.filtered(lambda mj: mj.subcontractor_id.id == subcontractor.id)]}})
        if sub_data:
            data.update({'sub_data': sub_data})
        return {
            'doc_ids': docids,
            'doc_model': 'mrp.barcode',
            'docs': records,
            'data': data}
