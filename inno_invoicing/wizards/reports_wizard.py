from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError, MissingError
from datetime import datetime


class ReportsWizard(models.TransientModel):
    _name = 'invoice.report.wizard'

    type = fields.Selection(
        [('master_key', 'Master Key'), ('cargo', 'Cargo'),('export_invoice', 'Export Invoice'),('order_sheet', 'Order Sheet')],
        string="Types")
    inno_package_id = fields.Many2one("inno.packaging")
    pdf = fields.Boolean("PDF")
    excel = fields.Boolean("EXCEL")

    @api.model
    def default_get(self, fields_list):
        rec = super().default_get(fields_list)
        package_id = self.env['inno.packaging'].browse(self._context.get('active_id'))
        if package_id:
            rec.update({'inno_package_id': package_id.id, })
        return rec

    def generate_reports(self):
        if self.pdf:
            report = False
            if self.type == 'cargo':
                report = self.env.ref('inno_invoicing.action_report_print_cargo_reports',
                                      ).report_action(docids=self.inno_package_id.id)
            elif self.type == 'export_invoice':
                report = self.env.ref('inno_invoicing.action_export_invoice_reports',
                                      ).report_action(docids=self.inno_package_id.id, data={'company': self.env['res.company'].search([], limit=1)})
            elif self.type == 'order_sheet':
                report = self.env.ref('inno_invoicing.action_report_print_order_sheet',
                                      ).report_action(docids=self.inno_package_id.id,
                                                      data={'company': self.env['res.company'].search([], limit=1)})
            return report
        if self.excel:
            data = {}
            report = self.env.ref('inno_invoicing.action_report_print_order_invoice_xlsx').report_action(self, data= data)
            return report

