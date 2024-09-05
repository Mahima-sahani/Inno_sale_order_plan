from odoo import fields, models, api, _
from odoo.exceptions import UserError


class ReturnJobWork(models.TransientModel):
    _name = 'inno.return.job.work'
    _description = 'Handel the cancellation process of Job Work'

    job_work_id = fields.Many2one(comodel_name='finishing.work.order')
    total_qty = fields.Integer(related ="job_work_id.total_qty", string="Quantity")
    scan_qty = fields.Integer(string="Scan Quantity", compute='_get_count')
    cancel_without_materials = fields.Boolean()
    barcode_ids = fields.Many2many(comodel_name='mrp.barcode', string="Barcode")
    penalty = fields.Float()
    raise_warning = fields.Boolean()
    return_date = fields.Date(default=fields.Datetime.now)
    display_warning = fields.Boolean()
    cancel_reason = fields.Text("Cancel Reason")


    @api.depends('barcode_ids')
    def _get_count(self):
        for rec in self:
            rec.scan_qty = len(self.barcode_ids.ids)

    @api.onchange('barcode_ids')
    def onchange_barcodes(self):
        if self.barcode_ids:
            jobwork_barcodes_lines  = self.job_work_id.jobwork_barcode_lines.filtered(lambda rec: rec.state == "draft" or rec.state == "rejected" )
            if self.job_work_id:
                correct_barcodes = self.barcode_ids.filtered(lambda bcode: bcode.id.origin
                                                                           in jobwork_barcodes_lines.barcode_id.ids
                                                                           and bcode.id.origin not in
                                                                           self.job_work_id.return_barcode_lines.ids )

                if not correct_barcodes:
                    self.display_warning = True
                else:
                    self.display_warning = False
                if correct_barcodes:
                    self.write({'barcode_ids': [(6, 0, correct_barcodes.ids)]})
                    self.display_warning = False
                else:
                    self.barcode_ids = False
                    self.display_warning = True


    def do_confirm(self):
        for rec in self.barcode_ids:
            line = self.job_work_id.jobwork_barcode_lines.filtered(
                lambda wo: rec.id in wo.barcode_id.ids)
            self.job_work_id.write({'return_barcode_lines': [(4, line.id)]})
        if self.cancel_without_materials or not self.job_work_id.material_lines:
            self.cancel_barcode_operation()
            self.job_work_id.full_cancellation_penalty = self.penalty
            self.add_barcode_penalty()
            if len(self.job_work_id.jobwork_barcode_lines) == len(self.job_work_id.return_barcode_lines):
                self.job_work_id.status = 'cancel'
        else:
            if self.job_work_id.material_transfer_id:
                self.cancel_barcode_operation()
                self.add_barcode_penalty()
                self.job_work_id.full_cancellation_penalty = self.penalty
                self.transfer_stock_from_subcontracter(self.total_qty)
            else:
                self.cancel_barcode_operation()
                self.add_barcode_penalty()
                self.job_work_id.full_cancellation_penalty = self.penalty
        if self.barcode_ids:
            self.barcode_ids.write({'location_id' : self.job_work_id.location_id.id})
        self.job_work_id.is_return = True
        self.job_work_id.return_reports_job_works()

    def cancel_barcode_operation(self):
        for rec in self.barcode_ids:
            wo = rec.current_process.filtered(
                lambda wo: self.job_work_id.operation_id.id in wo.workcenter_id.ids)
            vals ={}
            if wo:
                vals.update({
                    'current_process' : False,
                    'next_process' : wo.id
                })
                if len(rec.process_finished) == 1 and not rec.full_finishing:
                    vals.update({
                        'state' : '5_verified'
                    })
            else:
                vals.update({
                    'state': '5_verified',
                    'full_finishing': False
                })
            vals.update({
                'finishing_jobwork_id': False
            })
            rec.write(vals)
        for rec in self.job_work_id.return_barcode_lines:
            rec.state = 'cancel'
            rec.cancel_reason =  self.cancel_reason
        if self.total_qty == self.scan_qty:
            if self.job_work_id.material_transfer_id.state == 'draft':
                self.job_work_id.material_transfer_id.state = 'cancel'
            self.job_work_id.status = 'cancel'

    def add_barcode_penalty(self):
        for rec in self.barcode_ids:
            wo = rec.mrp_id.workorder_ids.filtered(
                lambda wo: self.job_work_id.operation_id.id in wo.workcenter_id.ids)
            rec.write({'current_process': False,
                                    'pen_inc_ids':
                                        [(0, 0, {'type': 'cancel', 'record_date': fields.Datetime.now(),
                                                 'amount': self.penalty, 'remark': f"{self.cancel_reason}",
                                                 'rec_id': self.job_work_id.id,
                                                 'workcenter_id': wo.id if wo else False,
                                                 'model_id': self.env.ref(
                                                     'inno_finishing.model_finishing_work_order').id})
                                         ]})

    def transfer_stock_from_subcontracter(self, product_qty=False):
        operation_type, source_location, destination_location = self.get_location_and_opoeration()
        try:
            job_stock_move = self.prepare_job_stock_move(source_location, destination_location, product_qty)
            if job_stock_move:
                vals = {
                    'name': operation_type.sequence_id.next_by_id(),
                    'partner_id': self.job_work_id.subcontractor_id.id,
                    'picking_type_id': operation_type.id,
                    'location_id': source_location,
                    'location_dest_id': destination_location,
                    'move_ids': job_stock_move,
                    'state': 'draft',
                    'finishing_work_id': self.job_work_id.id,
                    'origin': f"Cancel/Main Job Work: {self.job_work_id.name}"
                }
                self.env['stock.picking'].create(vals)
                if len(self.job_work_id.jobwork_barcode_lines) == len(self.job_work_id.return_barcode_lines):
                    self.job_work_id.write({'status': 'return_waiting'})
        except Exception as ex:
            raise UserError(_(ex))

    def get_location_and_opoeration(self):
        warehouse = self.env['inno.config'].sudo().search([], limit=1).main_warehouse_id
        if not warehouse:
            raise UserError(_("Please ask your admin to configure default warehouse."))
        operation_type = warehouse.out_type_id.return_picking_type_id
        source_location = self.env['stock.location'].search([('usage', '=', 'production')], limit=1).id
        dest_location = self.env['stock.location'].search([('usage', '=', 'supplier')], limit=1).id
        return operation_type, dest_location, source_location

    def prepare_job_stock_move(self, source_location, destination_location, product_qty):
        """
        Prepare the stock move line as per the component set in the selected operation
        """
        if self.job_work_id.material_lines:
            return_area = sum(self.job_work_id.return_barcode_lines.mapped('total_area'))
            to_return = [{'name': f"Transfer : {self.job_work_id.name}", 'product_id': rec.product_id.id,
                          'product_uom_qty': self.compute_return_qty(rec, return_area),
                          'product_uom': rec.uom_id.id, 'location_id': source_location,
                          'location_dest_id': destination_location}
                         for rec in self.job_work_id.material_lines if self.compute_return_qty(rec, return_area)]
            moves = [(0, 0, val) for val in to_return] if to_return else False
            return moves

    def compute_return_qty(self, rec, return_are):
        done_qty = sum(self.env['stock.picking'].search([('finishing_work_id', '=', self.job_work_id.id), ('state', '=', 'done')]).move_ids.filtered(lambda mid: mid.product_id.id == rec.product_id.id).mapped('quantity_done'))
        qty_required = (rec.product_qty / sum(self.job_work_id.jobwork_barcode_lines.mapped('total_area'))) * return_are
        if (rec.product_qty - done_qty) - qty_required < 0:
            return abs((rec.product_qty - done_qty) - qty_required)
        return False
