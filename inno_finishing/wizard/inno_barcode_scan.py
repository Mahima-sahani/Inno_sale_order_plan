from odoo import models, fields, api,_
from odoo.exceptions import UserError, ValidationError, MissingError


class InnoBarcodeScan(models.TransientModel):
    _inherit = 'inno.barcode.scan'

    def get_user_division(self):
        domain = [
            ('id', 'in', self.env.user.division_id.ids)]
        return domain

    division_id = fields.Many2one(comodel_name="mrp.division", string="Division", domain=get_user_division)



    @api.onchange('division_id')
    def onchange_division(self):
        self.barcode_ids = False

    def get_user_domain(self):
        transit_location_id = self.env.ref('inno_finishing.stock_location_transfer_wh').id
        vendor_location_id = self.env.ref('inno_finishing.stock_location_carpet_vendor_wh').id
        domain = [
            ('id', 'in', self.env.user.storage_location_ids.filtered(lambda sl: sl.id != transit_location_id and sl.id != vendor_location_id ).ids)]
        return domain

    location_id = fields.Many2one(comodel_name='stock.location', string='Bazaar Location',
                                  domain=get_user_domain)
    finishing_barcode_id = fields.Many2one(comodel_name='mrp.barcode')
    is_admin = fields.Boolean(compute='_check_admin')

    @api.depends('location_id')
    def _check_admin(self):
        for rec in self:
            rec.is_admin = True if self.env.user.has_group('inno_finishing.group_inno_finishing_admin') else False


    def do_confirm_finishing(self):
        main_job_works = self.barcode_ids.sudo().finishing_jobwork_id
        if self.barcode_ids:
            for job_work in main_job_works:
                if not job_work.baazar_lines_ids.filtered(lambda baz: baz.date == fields.Datetime.today().date()):
                    self.env['finishing.baazar'].sudo().create(
                        {'finishing_work_id': job_work.id, 'subcontractor_id': job_work.subcontractor_id.id,
                         'state': 'qc', 'is_external': job_work.is_external, })
                job_work.status = 'baazar'
                bazaar = job_work.baazar_lines_ids.filtered(lambda baz: baz.date == fields.Datetime.today().date())
                bazaar.write({
                    'jobwork_received_ids': [(0, 0, {'finishing_work_id': job_work.id, 'state': 'received',
                                                     'work_order_line_id' : job_work.sudo().jobwork_barcode_lines.
                                              filtered(lambda pd: bcode.id in pd.barcode_id.ids).id,
                                                     'barcode_id': bcode.id,'rate':  job_work.sudo().jobwork_barcode_lines.
                                              filtered(lambda pd: bcode.id in pd.barcode_id.ids).rate}) for bcode in
                                         self.barcode_ids.filtered(
                                             lambda sbcode: sbcode.finishing_jobwork_id.id == job_work.id) if bcode],
                    'location_id': self.location_id.id})
                line_barcodes = job_work.jobwork_barcode_lines.filtered(lambda baz: baz.barcode_id.id in self.barcode_ids.ids)
                line_barcodes.write({'state': 'received'})
            barcode_ids = self.barcode_ids.ids
            self.barcode_ids = False
            report = self.env.ref('inno_finishing.action_report_print_bazaar_finishing_receiving',
                                  raise_if_not_found=False).report_action(docids=barcode_ids)
            return report


    @api.onchange('finishing_barcode_id')
    def onchange_finishing_barcodes(self):
        if self.finishing_barcode_id:
            message = self.check_barcode_finishing()
            if not message:
                self.write({'barcode_ids': [(4, self.finishing_barcode_id.id)]})
                self.display_warning = False
                self.success_message = (f"Subcontractor: {self.finishing_barcode_id.sudo().finishing_jobwork_id.subcontractor_id.name} <| |> Size: {self.finishing_barcode_id.size}"
                                        f" <| |> SKU: {self.finishing_barcode_id.product_id.default_code}")
                self.finishing_barcode_id = False
            else:
                self.success_message = False
                self.display_warning = message
                self.finishing_barcode_id = False

    def check_barcode_finishing(self):
        message = False
        receives_lines = self.finishing_barcode_id.sudo().finishing_jobwork_id.jobwork_barcode_lines
        if self.finishing_barcode_id.state not in ['7_finishing']:
            message = (f'You have scanned the barcode is in {self.barcode_id.state} stage.\n Only barcode with Finishing'
                       f' state can be scanned')
        elif self.finishing_barcode_id.division_id.id != self.division_id.id:
            message = "You can only receive products of your own division"
        elif self.finishing_barcode_id and receives_lines.filtered(lambda bl: bl.barcode_id.id == self.finishing_barcode_id.id
                                                                  and bl.state == 'received'):
            message = "This Barcode is already received and waiting for QC."
        elif not receives_lines:
            message = "You have scanned the barcode that is already received or not associated with any job work "
        elif self.finishing_barcode_id.finishing_jobwork_id.sudo().status in ['draft','allotment',]:
            message = "This barcode status is Draft or Awaiting Release"
        elif(self.finishing_barcode_id.id in self.finishing_barcode_id.sudo().
                finishing_jobwork_id.baazar_lines_ids.filtered(lambda baz: baz.date == fields.Datetime.today().date()).jobwork_received_ids.barcode_id.ids):
            message = "This barcode already received today"
        return message


