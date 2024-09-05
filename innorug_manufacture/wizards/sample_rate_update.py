from odoo import models, fields, api


class SampleRateUpdate(models.TransientModel):
    _name = 'sample.rate.update'

    rate = fields.Float(digits=(8, 3), string='Add Rate')

    def confirm_update(self):
        mrp_line = self.env['mrp.job.work'].browse(self._context.get('active_id'))
        mrp_line.original_rate = self.rate
        if mrp_line.main_jobwork_id.state not in ['draft']:
            mrp_line.rate = self.rate
        mrp_line.main_jobwork_id.message_post(body=f"<b>Updated Sample Rate:</b><br/> <b>{self.rate} ₹</b> "
                                                   f"for <b>product {mrp_line.product_id.default_code}</b>")
