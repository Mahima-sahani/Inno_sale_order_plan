from odoo import models, fields, api


class BarcodeInfo(models.TransientModel):
    _name = 'inno.barcode.info'
    _description = 'information about barcode'

    barcode_id = fields.Many2one(comodel_name='mrp.barcode', string='Barcode')
    barcode_info = fields.Html(string='Barcode Info')
    operation_info = fields.Html(string='Operation Info')

    @api.onchange('barcode_id')
    def onchange_barcode_id(self):
        barcode_state = {'1_draft': 'Draft', '2_allotment': 'Job Allotment', '3_allocated': 'Job Allocated',
                         '4_received': 'Weaving Received', '5_verified': 'Weaving Completed',
                         '6_rejected': 'Weaving Rejected', '7_finishing': 'Finishing', '8_done': "Manufacturing Done",
                         '9_packaging': 'Packed', '10_done': 'Shipped'}
        self.barcode_info = f"""
                <div class="row">
                    <div class="col-6">
                        <span><b>Design:</b></span>
                        <span><b>{self.barcode_id.design}</b></span>
                    </div>
                    <div class="col-6">
                        <span><b>SKU:</b></span>
                        <span><b>{self.barcode_id.product_id.default_code}</b></span>
                    </div>
                    <hr/>
                    <div class="col-6">
                        <span><b>State:</b></span>
                        <span>{barcode_state.get(self.barcode_id.state)}</span>
                    </div>
                    <div class="col-6">
                        <span><b>Size:</b></span>
                        <span>{self.barcode_id.size}</span>
                    </div>
                    <hr/>
                    <div class="col-6">
                        <span><b>Sale Order:</b></span>
                        <span>{self.barcode_id.sudo().sale_id.name}</span>
                    </div>
                    <hr/>
                    <div class="col-6">
                        <span><b>Current Operation:</b></span>
                        <span>{self.barcode_id.sudo().current_process.name}</span>
                    </div>
                    <div class="col-6">
                        <span><b>Next Operation:</b></span>
                        <span>{self.barcode_id.sudo().next_process.name}</span>
                    </div>
                     <hr/>
                     <div class="col-6">
                        <span><b>Location:</b></span>
                        <span>{self.barcode_id.sudo().location_id.location_id.name}</span>
                    </div>
                </div>
        """
        if self.barcode_id:
            data = f"""
            <table class="table table-striped">
              <thead>
                <tr>
                  <th scope="col">Operation</th>
                  <th scope="col">Date</th>
                  <th scope="col">Subcontractor</th>
                  <th scope="col">Job Work Number</th>
                  <th scope="col">State</th>
                </tr>
              </thead>
              <tbody>
                {self.get_barcode_info()}
              </tbody>
            </table>
            """
            self.operation_info = data
        else:
            self.barcode_info = False
            self.operation_info = False

    def get_barcode_info(self):
        job_state = {'draft': 'DRAFT', 'allotment': 'WAITING RELEASE', 'release': 'RELEASE', 'qa': 'PROCESS QC',
                     'baazar': 'BAAZAR', 'done': 'JOB FINISHED', 'return_waiting': 'WAITING FOR MATERAIL RETURN',
                     'cancel': 'CANCELLED', 'received': 'RECEIVED', 'verified': 'VERIFIED', 'reject': 'Rejected'}
        data = ""
        query = f"select mrp_job_work_id from mrp_barcode_mrp_job_work_rel where mrp_barcode_id = {self.barcode_id.id}"
        self._cr.execute(query)
        job_works = self.env['mrp.job.work'].browse([x[0] for x in self._cr.fetchall()]).sudo().main_jobwork_id
        for job in job_works:
            data += f"""
                    <tr>
                      <td>Weaving</td>
                      <td>{job.issue_date}</td>
                      <td>{job.subcontractor_id.name}</td>
                      <td>{job.reference}</td>
                      <td>{job_state.get(job.state)}</td>
                    </tr>
                """
        for bazaar in self.env['mrp.baazar.product.lines'].search([('barcode', '=', self.barcode_id.id)]):
            data += f"""
                        <tr>
                          <td>Bazaar</td>
                          <td>{bazaar.date}</td>
                          <td>{bazaar.sudo().bazaar_id.subcontractor_id.name}</td>
                          <td>{bazaar.sudo().bazaar_id.reference}</td>
                          <td>{job_state.get(bazaar.state)}</td>
                        </tr>
                    """
        return data
