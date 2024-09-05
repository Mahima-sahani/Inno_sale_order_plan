from odoo import models, fields, api,_
from odoo.exceptions import UserError, ValidationError, MissingError

class FinishingOperation(models.TransientModel):
    _name = 'finishing.operation.wizard'

    def get_user_domain(self):
        transit_location_id = self.env.ref('inno_finishing.stock_location_transfer_wh').id
        domain = [('id', 'in', self.env.user.storage_location_ids.filtered(lambda sl: sl.id != transit_location_id).ids)]
        return domain

    def get_user_division(self):
        print(self.env.user.division_id.ids)
        domain = [
            ('id', 'in', self.env.user.division_id.ids)]
        return domain

    operation_id = fields.Many2one("mrp.workcenter", string="Operation")
    external = fields.Boolean("External")
    subcontractor_id = fields.Many2one(comodel_name='res.partner', string="Person")
    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.user)
    expected_date = fields.Date()
    source_location_id = fields.Many2one(comodel_name='stock.location', string="Source Location",domain=get_user_domain)
    dest_location_id = fields.Many2one(comodel_name='stock.location', string="Destination Location")
    remarks = fields.Text(string="Remarks")
    issue_date = fields.Datetime(default=fields.Datetime.now, string="Date")
    division_id = fields.Many2one(comodel_name="mrp.division", string="Division", domain=get_user_division)
    skip_reason = fields.Text("Reason")
    barcode_id = fields.Many2one("mrp.barcode")
    skip_operation = fields.Many2one(related ="barcode_id.next_process", string="Skip Operation")
    next_operation = fields.Many2one('mrp.workorder', string="Next Operation")
    is_admin = fields.Boolean(compute='_check_admin')
    #Barcode scan
    barcode_ids = fields.Many2many(comodel_name='mrp.barcode')
    display_warning = fields.Char()
    remove_barcode_id = fields.Many2one(comodel_name='mrp.barcode')
    scan_count = fields.Integer(string='Total Scanned Barcodes', compute='_compute_scan_count')
    success_message = fields.Char()
    job_worker_code = fields.Char("Code")
    is_reset = fields.Boolean()

    @api.onchange('division_id')
    def onchange_division(self):
        self.barcode_ids = False
        self.subcontractor_id = False
        self.success_message = False

    @api.onchange('job_worker_code')
    def onchange_get_vendor_name(self):
        if self.job_worker_code:
            code = self.env['res.partner'].search([('job_worker_code', '=', self.job_worker_code)])
            if code:
                self.write({'subcontractor_id' : code.id,'barcode_ids': False,})
                self._compute_scan_count()

    @api.onchange('subcontractor_id')
    def onchange_barcodes_ids(self):
        self.write({'barcode_ids': False})
        self._compute_scan_count()

    @api.onchange('source_location_id')
    def onchange_user_id(self):
        transit_location_id = self.env.ref('inno_finishing.stock_location_transfer_wh').id
        internal_locations = self.env['stock.location'].search([('usage', '=', 'internal')])
        if self.source_location_id:
            domain = [
                ('id', 'in', internal_locations.filtered(lambda sl: sl.id != transit_location_id and sl.id != self.source_location_id.id).ids)]
            return {'domain': {'dest_location_id': domain}}
        else:
            return {'domain': {'dest_location_id': []}}

    def _compute_scan_count(self):
        for rec in self:
            rec.scan_count = self.barcode_ids.__len__()

    def check_barcode(self):
        is_true = False
        config_id = self.env["inno.config"].sudo().search([], limit=1)
        if (self.operation_id == config_id.full_finishing_id
                and self.barcode_id.id not in self.barcode_ids.ids
                and self.barcode_id.filtered(lambda bcode: bcode.state in ['5_verified']
                                                           and not bcode.full_finishing
                                                           and not bcode.finishing_jobwork_id
                                                           and not bcode.current_process and not bcode.transfer_id and self.source_location_id.id == bcode.location_id.id)):
            # self.barcode_id.update({'full_finishing': True})
            is_true = True
        elif (self.operation_id == config_id.full_finishing_id
                and self.barcode_id.id not in self.barcode_ids.ids
                and self.barcode_id.filtered(lambda bcode: bcode.state in ['7_finishing', ] and bcode.process_finished.filtered(lambda wo: config_id.washing_id.id in wo.workcenter_id.ids and len(bcode.process_finished)==2)
                                                           and not bcode.full_finishing
                                                           and not bcode.finishing_jobwork_id
                                                           and not bcode.current_process and not bcode.transfer_id and self.source_location_id.id == bcode.location_id.id)):
            is_true = True
        elif (self.operation_id == config_id.full_finishing_id
              and self.barcode_id.id not in self.barcode_ids.ids
              and self.barcode_id.filtered(
                    lambda bcode: bcode.state in ['7_finishing', ]
                                  and not bcode.full_finishing
                                  and not bcode.finishing_jobwork_id
                                  and not bcode.current_process and not bcode.transfer_id and self.source_location_id.id == bcode.location_id.id)):
            is_true = True
        elif (self.barcode_id.filtered(lambda bcode: bcode.state in [
            '5_verified', '7_finishing'] and not bcode.full_finishing and
                                                     self.operation_id.id == bcode.next_process.sudo().workcenter_id.id
                                                     and not bcode.current_process and not bcode.finishing_jobwork_id
                                                     and bcode.id not in self.barcode_ids.ids and not bcode.transfer_id and self.source_location_id.id == bcode.location_id.id)):
            is_true = True
            self.barcode_id.next_process.button_start()
        elif (self.barcode_id.filtered(lambda bcode: self.operation_id.id ==  bcode.next_process.sudo().workcenter_id.id
                                                     and not bcode.finishing_jobwork_id and bcode.full_finishing
                                                     and bcode.id not in self.barcode_ids.ids
                                                     and not self.barcode_id.current_process and not bcode.transfer_id and self.source_location_id.id == bcode.location_id.id )):
            is_true = True
            self.barcode_id.next_process.button_start()
        return is_true

    def check_work_order(self):
        is_true = True
        self.barcode_id.next_process.button_start()
        if self.barcode_id.next_process.state != 'progress':
            self.display_warning = False
            self.start_wo = self.barcode_id.mrp_id.sudo().name
            self.barcode_id = False
            is_true =  False
        return is_true

    def barcode_status_rcord(self):
        is_true = True
        if self.division_id != self.barcode_id.division_id:
            self.display_warning = self.barcode_id.division_id.name
            is_true = False
        if self.barcode_id.id in self.barcode_ids.ids:
            self.display_warning = "Already Scanned"
            is_true = False
        elif (self.barcode_id.finishing_jobwork_id):
            self.display_warning =  f"This barcode is associated with '{self.barcode_id.finishing_jobwork_id.name}'"
            is_true = False
        elif(self.barcode_id.transfer_id):
            self.display_warning = "This barcode is transfer mode"
            is_true = False
        elif(self.barcode_id.location_id != self.source_location_id):
            self.display_warning = f"This barcode location is '{self.barcode_id.location_id.location_id.name}/{self.barcode_id.location_id.name}'"
            is_true = False
        if(self.barcode_id.state in ['1_draft','2_allotment','3_allocated','4_received']):
            self.display_warning = "Weaving Process"
            is_true = False
        return is_true
    @api.onchange('barcode_id')
    def onchange_barcodes(self):
        if self.operation_id:
            # if not self.division_id:
            #     self.division_id = self.user_id.division_id.id
            if not self.division_id:
                self.display_warning = "First select your division"
            is_check_status = self.barcode_status_rcord()
            if is_check_status:
                is_barcoede_correct = self.check_barcode()
                if is_barcoede_correct:
                    self.write({'barcode_ids': [(4, self.barcode_id.id)]})
                    self.success_message = (
                        f"Design: {self.barcode_id.design} <| |> Size: {self.barcode_id.size}"
                        f" <| |> SKU: {self.barcode_id.product_id.default_code}")
                    self._compute_scan_count()
                    self.barcode_id = False
                    self.display_warning = False
                else:
                    self.barcode_id = False
                    self.success_message = False
                    self.display_warning = 'You have scanned the barcode that is already received or not associated with current job work '
            elif(self.display_warning):
                self.barcode_id = False
                self.success_message = False
        else:
            if self.source_location_id and self.dest_location_id:
                if self.barcode_id.filtered(lambda bcode: bcode.state in
                                                          ['5_verified', '7_finishing', '8_done', '9_done'] and
                                                          bcode.location_id.id in self.source_location_id.ids  and
                                                          bcode.location_id.id not in self.dest_location_id.ids and
                                                    not bcode.finishing_jobwork_id and not bcode.current_process and
                                                           not bcode.transfer_id ):
                    self.write({'barcode_ids': [(4, self.barcode_id.id)]})
                    self.success_message = (
                        f"Design: {self.barcode_id.design} <| |> Size: {self.barcode_id.size}"
                        f" <| |> SKU: {self.barcode_id.product_id.default_code}")
                    self._compute_scan_count()
                    self.barcode_id = False
                    self.display_warning = False
                else:
                    self.barcode_id = False
                    self.success_message = False
                    self.display_warning = 'You have scanned the barcode that is already transfer or not associated with source location '
            else:
                if self.barcode_id.transfer_id.dest_location_id.id in self.env.user.storage_location_ids.ids:
                    self.write({'barcode_ids': [(4, self.barcode_id.id)]})
                    self.success_message = (
                        f"Design: {self.barcode_id.design} <| |> Size: {self.barcode_id.size}"
                        f" <| |> SKU: {self.barcode_id.product_id.default_code}")
                    self._compute_scan_count()
                    self.barcode_id = False
                    self.display_warning = False
                elif(self.barcode_id):
                    self.barcode_id = False
                    self.success_message = False
                    self.display_warning = 'You have scanned the barcode that is already transfer or not associated with destination location '

    @api.onchange('remove_barcode_id')
    def onchange_remove_barcodes(self):
        if self.remove_barcode_id:
            self.write({'barcode_ids': [(3, self.remove_barcode_id.id)]})
            self._compute_scan_count()
            self.remove_barcode_id = False

    @api.depends('operation_id')
    def _check_admin(self):
        for rec in self:
            rec.is_admin = True if self.env.user.has_group('inno_finishing.group_inno_finishing_admin') else False

    def do_confirm_reason(self):
        if self.skip_operation and self.next_operation and self.skip_reason:
            for rec in self.skip_operation:
                rec.finished_qty +=1
            self.barcode_id.write({'next_process': self.next_operation.id})
            self.barcode_id.message_post(body=f'Process <b>{self.skip_operation.name}</b> is Skipped<br/><b>Reason:</b><br/>{self.skip_reason}')

    @api.onchange('operation_id')
    def set_external(self):
        config_id = self.env["inno.config"].sudo().search([], limit=1)
        # if not self.is_admin:
        #     self.division_id = self.user_id.division_id.id
        if (self.operation_id == config_id.full_finishing_id):
            self.external = True
        else:
            self.external = False

    def do_transfer_confirm(self):
        self.operation_id.get_sequence()
        vals = {'source_location_id': self.source_location_id.id,
                'dest_location_id': self.dest_location_id.id,
                "person_id": self.subcontractor_id.id, "remarks": self.remarks,
                "issue_date": self.issue_date}
        transfer = self.env['inno.carpet.transfer'].sudo().create(vals)
        transfer.write({'barcode_line': [(0, 0, {"barcode_id": bcode.id,}) for
                                      bcode in
                                      self.barcode_ids]})
        self.barcode_ids.write({'transfer_id': transfer.id, 'location_id': self.env.ref('inno_finishing.stock_location_transfer_wh').id})
        # return self.button_for_transfer_wizard(transfer)

    # def button_for_transfer_wizard(self, transfer):
    #     return {
    #         'name': 'Transfer',
    #         'view_mode': 'form',
    #         'res_model': 'inno.carpet.transfer',
    #         'type': 'ir.actions.act_window',
    #         'target': 'currebt',
    #         'res_id': transfer.id
    #     }

    def do_confirm(self):
        if self.barcode_ids:
            barcode = self.barcode_ids.filtered(lambda br: not br.finishing_jobwork_id)
            vendor_location_id = self.env.ref('inno_finishing.stock_location_carpet_vendor_wh')
            if barcode:
                if not self.is_admin:
                    self.division_id = self.user_id.division_id.id
                self.sudo().operation_id.get_sequence()
                vals = {'name': self.operation_id.sequence_id.next_by_id(), 'operation_id': self.operation_id.id, 'status': 'draft','division_id' : self.division_id.id,
                        "subcontractor_id": self.subcontractor_id.id, "is_external": self.external, 'location_id' : self.source_location_id.id, "alloted_days": 10,
                        "expected_date": self.expected_date}
                f_work_id = self.env['finishing.work.order'].sudo().create(vals)
                f_work_id.write({
                    'jobwork_barcode_lines': [(0, 0,
                                              {"barcode_id": bcode.id,}) for bcode in
                                             barcode]})
                barcode.write({'finishing_jobwork_id': f_work_id.id, 'location_id' : vendor_location_id.id})
                # f_work_id.create_rate_list_data(f_work_id)
                f_work_id.onchange_alloted_days()
                f_work_id.create_rate_list_data()
                config_id = self.env["inno.config"].sudo().search([], limit=1)
                if (self.operation_id == config_id.full_finishing_id) and barcode:
                    barcode.write({'full_finishing': True})
            self.write({ 'subcontractor_id' : False,'barcode_ids' : False})
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'success',
                    'message': "Record Created Successfully",
                }
            }


    def button_for_operation_wizard(self,f_work_id):
        return {
            'name': 'Finishing Operation',
            'view_mode': 'form',
            'res_model': 'finishing.work.order',
            'type': 'ir.actions.act_window',
            'target': 'current',
            'res_id': f_work_id.id
        }

    def do_transfer_received_confirm(self):
       is_true= self.env['inno.carpet.transfer'].change_transfer_status(self.barcode_ids)
       if is_true:
           for rec in self.barcode_ids:
               rec.write({'transfer_id': False,})

