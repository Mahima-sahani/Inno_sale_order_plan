from odoo import models, fields, api, _
from odoo.exceptions import UserError


class InnoBarcodeInfoF(models.TransientModel):
    _inherit = 'inno.barcode.info'


    def get_barcode_info(self):
        vals = super().get_barcode_info()
        job_state = {'draft': 'DRAFT', 'allotment': 'WAITING RELEASE', 'release': 'RELEASE', 'qa': 'PROCESS QC',
                     'baazar': 'BAAZAR', 'done': 'JOB FINISHED', 'return_waiting': 'WAITING FOR MATERAIL RETURN',
                     'cancel': 'CANCELLED', 'received': 'RECEIVED', 'verified': 'VERIFIED', 'reject': 'Rejected'}
        data = ""
        job_works_lines = self.env["jobwork.barcode.line"].sudo().search([('barcode_id', '=', self.barcode_id.id)])
        for job in job_works_lines:
            data += f"""
                    <tr>
                      <td>{job.finishing_work_id.operation_id.name}</td>
                      <td>{job.finishing_work_id.issue_date}</td>
                      <td>{job.finishing_work_id.subcontractor_id.name}</td>
                      <td>{job.finishing_work_id.name}</td>
                      <td>{job_state.get(job.finishing_work_id.status)}</td>
                    </tr>
                """
            for bazaar in self.env["jobwork.received"].search([('barcode_id', '=', self.barcode_id.id),('finishing_work_id', '=', job.finishing_work_id.id)]):
                data += f"""
                                       <tr>
                                         <td>Receiving</td>
                                         <td>{bazaar.sudo().baazar_id.date}</td>
                                         <td>{bazaar.sudo().baazar_id.subcontractor_id.name}</td>
                                         <td>{bazaar.sudo().baazar_id.reference}</td>
                                         <td>{job_state.get(bazaar.state)}</td>
                                       </tr>
                                   """
        return vals + data