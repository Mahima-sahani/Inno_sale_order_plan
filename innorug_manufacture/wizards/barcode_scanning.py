from odoo import models, fields, api, _
from odoo.exceptions import UserError


class InnoBarcodeScanning(models.TransientModel):
    _name = 'inno.barcode.scan'
    _description = 'Used to receive all barcodes in one go'

    barcode_ids = fields.Many2many(comodel_name='mrp.barcode')
    display_warning = fields.Char()
    barcode_id = fields.Many2one(comodel_name='mrp.barcode')
    location_id = fields.Many2one(comodel_name='stock.location', string='Bazaar Location', )
    remove_barcode_id = fields.Many2one(comodel_name='mrp.barcode')
    scan_count = fields.Integer(string='Total Scanned Barcodes', compute='_compute_scan_count')
    success_message = fields.Char()

    @api.depends('barcode_ids')
    def _compute_scan_count(self):
        for rec in self:
            rec.scan_count = self.barcode_ids.__len__()

    @api.onchange('barcode_id')
    def onchange_barcodes(self):
        if self.barcode_id:
            message = self.check_barcode()
            if not message:
                self.write({'barcode_ids': [(4, self.barcode_id.id)]})
                self.display_warning = False
                self.success_message = (
                    f"SubContractor: {self.barcode_id.sudo().main_job_work_id.subcontractor_id.name} <| |>"
                    f" Design: {self.barcode_id.design} <| |> Size: {self.barcode_id.size}"
                    f" <| |> SKU: {self.barcode_id.sudo().product_id.default_code}")
                self.barcode_id = False
            else:
                self.success_message = False
                self.display_warning = message
                self.barcode_id = False

    @api.onchange('remove_barcode_id')
    def onchange_remove_barcodes(self):
        if self.remove_barcode_id:
            self.write({'barcode_ids': [(3, self.remove_barcode_id.id)]})
            self.remove_barcode_id = False

    def check_barcode(self):
        message = False
        bazaar_lines = self.barcode_id.sudo().main_job_work_id.baazar_lines_ids.baazar_lines_ids
        if self.barcode_id.state != '3_allocated':
            message = (
                f'You have scanned the barcode is in {self.barcode_id.state} stage.\n Only barcode with Allocated'
                f' state can be scanned')
        elif self.barcode_id.division_id.id != self.env.user.division_id.id:
            message = "You can only receive products of your own division"
        elif self.barcode_id and bazaar_lines.filtered(lambda bl: bl.barcode.id == self.barcode_id.id
                                                                  and bl.state == 'received'):
            message = "This Barcode is already received and waiting for QC."
        elif self.barcode_id and bazaar_lines.filtered(lambda bl: bl.barcode.id == self.barcode_id.id
                                                                  and bl.state == 'verified'):
            message = "This barcode has already completed the weaving process"
        elif (self.barcode_id and self.barcode_id.sudo().main_job_work_id.quality_control_ids.
                filtered(lambda qc: qc.quality_state == 'draft')):
            message = "Loom Inspection for this bazaar is not Completed."
        # elif bazaar_lines.filtered(lambda baz: baz.date == fields.Datetime.today().date() and baz.state != 'receiving'):
        #     message = "Bazaar associated for this barcord is completed for today.\n Please try again tommorrow"
        try:
            self.barcode_id.sudo().main_job_work_id.validate_pickings()
        except:
            message = (f"Material is not released for this barcode associated to Job "
                       f"work {self.barcode_id.sudo().main_job_work_id.reference}")
        return message

    def do_confirm(self):
        main_job_works = self.barcode_ids.sudo().main_job_work_id
        if not self.barcode_ids:
            return False
        for job_work in main_job_works:
            if not job_work.baazar_lines_ids.filtered(lambda baz: baz.date.date() == fields.Datetime.today().date()):
                job_work.button_ready_bazaar()
            bazaar = job_work.baazar_lines_ids.filtered(lambda baz: baz.date.date() == fields.Datetime.today().date())
            bazaar.write({
                'baazar_lines_ids': [(0, 0, {'main_jobwork_id': job_work.id, 'state': 'received', 'barcode': bcode.id,
                                             'job_work_id': main_job_works.jobwork_line_ids.filtered(
                                                 lambda jw: bcode.id in jw.barcodes.ids).id}) for bcode in
                                     self.barcode_ids.filtered(lambda sbcode: sbcode.main_job_work_id.id == job_work.id)
                                     if not self.env['mrp.baazar.product.lines'].search([('barcode', '=', bcode.id),('state', '=', 'received')])],
                'location_id': self.location_id.id})
        barcode_ids = self.barcode_ids.ids
        self.barcode_ids = False
        report = False
        if main_job_works:
            report = self.env.ref('innorug_manufacture.action_report_print_bazaar_receiving',
                                  raise_if_not_found=False).report_action(docids=barcode_ids)
        return report
