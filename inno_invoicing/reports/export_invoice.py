import datetime
from odoo import models, api


class ReportExportInvoice(models.AbstractModel):
    _name = 'report.inno_invoicing.templete_action_id'
    _description = 'Will prepare the data for displaying the template.'

    @api.model
    def _get_report_values(self, docids, data=None):
        record = self.env['inno.packaging'].browse(docids)
        pass