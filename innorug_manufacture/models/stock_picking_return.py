from odoo import models

class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    def create_returns(self):
        rec = super().create_returns()
        try:
            main_job_id = self.env['stock.picking'].browse(rec.get('context').get('active_id')).main_jobwork_id.id
        except:
            pass
        if main_job_id:
            rec.get('context').update({'main_jobwork_id': main_job_id})
        return rec
