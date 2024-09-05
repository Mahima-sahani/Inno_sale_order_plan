from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CancelJobWork(models.TransientModel):
    _name = 'inno.cancel.job.work'
    _description = 'Handel the cancellation process of Job Work'

    def get_barcode_domain(self):
        barcodes_in_bazaar = (self.job_work_id.baazar_lines_ids.baazar_lines_ids.
                              filtered(lambda bl: bl.state in ['received', 'verified'])).barcode.ids
        barcode_ids = (self.job_work_id.browse(self._context.get('default_job_work_id')).jobwork_line_ids.barcodes.
                       filtered(lambda bcode: bcode.state == '3_allocated' and bcode.id not in barcodes_in_bazaar).ids)
        return [('id', 'in', barcode_ids)]

    job_work_id = fields.Many2one(comodel_name='main.jobwork')
    full_cancellation = fields.Boolean()
    cancel_without_materials = fields.Boolean()
    barcode_ids = fields.Many2many(comodel_name='mrp.barcode', domain=get_barcode_domain)
    penalty = fields.Float()
    raise_warning = fields.Boolean()

    @api.onchange('full_cancellation')
    def onchange_barcodes(self):
        if self.full_cancellation:
            if (self.job_work_id.baazar_lines_ids.baazar_lines_ids.
                    filtered(lambda bl: bl.state in ['received', 'verified'])):
                self.write({'full_cancellation': False, 'raise_warning': True})

    def do_confirm(self):
        if not self.full_cancellation and not self.barcode_ids:
            raise UserError(_("Please select some barcodes to cancel"))
        if self.full_cancellation:
            barcodes = self.job_work_id.jobwork_line_ids.barcodes
            self.job_work_id.write({'cancelled_barcodes': [(4, bcode.id) for bcode in barcodes]})
            barcodes.write({'state': '1_draft', 'main_job_work_id': False, 'current_process': False})
            if self.penalty > 0.0:
                self.env['inno.incentive.penalty'].create({
                    'partner_id': self.job_work_id.subcontractor_id.id,
                    'remark': f"Cancelled the job work {self.job_work_id.reference}",
                    'record_date': fields.Datetime.now(),
                    'amount': self.penalty,
                    'type': 'cancel'
                })
            for rec in self.job_work_id.jobwork_line_ids:
                rec.return_quantity = rec.product_qty
        else:
            self.barcode_ids.write({'state': '1_draft', 'main_job_work_id': False, 'current_process': False})
            if self.penalty > 0.0:
                self.add_barcode_penalty()
            self.job_work_id.write({'cancelled_barcodes': [(4, bcode.id) for bcode in self.barcode_ids]})
        if self.cancel_without_materials and self.full_cancellation:
            self.job_work_id.state = 'cancel'
        elif self.full_cancellation:
            picking = self.transfer_stock_from_subcontracter()
            if picking:
                self.job_work_id.write({'state': 'return_waiting'})
        else:
            product_qty = {pid: len([bcode.name for bcode in self.barcode_ids if bcode.product_id.id == pid])
                           for pid in self.barcode_ids.product_id.ids}
            self.transfer_stock_from_subcontracter(product_qty)
        self.job_work_id.jobwork_line_ids.mrp_work_order_id._compute_allotment_status()
        self.job_work_id.print_cancelled_barcodes()

    def add_barcode_penalty(self):
        self.barcode_ids.write({'state': '1_draft', 'main_job_work_id': False, 'current_process': False,
                                'pen_inc_ids':
                                    [(0, 0, {'type': 'cancel', 'record_date': fields.Datetime.now(),
                                             'amount': self.penalty, 'remark': "Cancelled the Job",
                                             'rec_id': self.job_work_id.id,
                                             'workcenter_id': self.barcode_ids.current_process.id,
                                             'model_id': self.env.ref('innorug_manufacture.model_main_jobwork').id,
                                             'partner_id': self.job_work_id.subcontractor_id.id})
                                     ]})
        for jw in self.job_work_id.jobwork_line_ids:
            jw.return_quantity = len(self.barcode_ids.filtered(lambda bcode: bcode.id in jw.barcodes.ids))

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
                    'main_jobwork_id': self.job_work_id.id,
                    'origin': f"Cancel/Main Job Work: {self.job_work_id.reference}"
                }
                return self.env['stock.picking'].create(vals)
        except Exception as ex:
            raise UserError(_(ex))

    def get_location_and_opoeration(self):
        if not self.env.user.material_location_id:
            raise UserError(_("Please Ask Your Admin to set your Material Location."))
        warehouse = self.env.user.material_location_id.warehouse_id
        operation_type = warehouse.out_type_id.return_picking_type_id
        source_location = self.env.user.material_location_id.id
        dest_location = self.env['stock.location'].search([('usage', '=', 'supplier')], limit=1).id
        return operation_type, dest_location, source_location

    def prepare_job_stock_move(self, source_location, destination_location, product_qty):
        """
        Prepare the stock move line as per the component set in the selected operation
        """
        if product_qty:
            allotment_vals = dict()
            for raw_moves in (self.job_work_id.jobwork_line_ids.filtered(lambda jwl: jwl.product_id.id in product_qty.keys()).
                    mrp_work_order_id.move_raw_ids):
                jobwork_id = self.job_work_id.jobwork_line_ids.filtered(lambda jwl: jwl.mrp_work_order_id.id == raw_moves.workorder_id.id)
                if raw_moves.product_id.id in allotment_vals.keys():
                    existing_data = allotment_vals.get(raw_moves.product_id.id)
                    existing_data.update(
                        {'product_uom_qty': existing_data.get('product_uom_qty') + (raw_moves.product_qty / raw_moves.workorder_id.qty_production) * product_qty.get(jobwork_id.product_id.id)})
                else:
                    allotment_vals[raw_moves.product_id.id] = {'name': f"Transfer : {self.job_work_id.reference}",
                                                               'product_id': raw_moves.product_id.id,
                                                               'product_uom_qty': (raw_moves.product_qty / raw_moves.workorder_id.qty_production) * product_qty.get(jobwork_id.product_id.id),
                                                               'product_uom': raw_moves.product_uom.id,
                                                               'location_id': source_location,
                                                               'location_dest_id': destination_location}
            allotment_vals = self.update_allotment(allotment_vals.values(), False)
            moves = [(0, 0, val) for val in allotment_vals] if allotment_vals else False
        else:
            vals = [{'name': f"Transfer : {self.job_work_id.reference}", 'product_id': component.product_id.id,
                             'product_uom_qty': component.alloted_quantity, 'product_uom': component.product_uom.id,
                             'location_id': source_location, 'location_dest_id': destination_location}
                    for component in self.job_work_id.product_allotment_ids]
            vals = self.update_allotment(vals, True)
            moves = [(0, 0, val) for val in vals] if vals else False
        return moves

    def update_allotment(self, vals, full_cancel):
        pickings = self.env['stock.picking'].search([('main_jobwork_id', '=', self.job_work_id.id)])
        pickings.filtered(lambda pick:pick.state != 'done').action_cancel()
        done_pickings = pickings.filtered(lambda pick: pick.state == 'done')
        new_vals = []
        for val in vals:
            total_qty = sum(self.job_work_id.alloted_material_ids.
                            filtered(lambda alot: alot.product_id.id == val.get('product_id')).
                            mapped('alloted_quantity')) + sum(self.job_work_id.alloted_material_ids.
                                                              filtered(lambda alot: alot.product_id.id == val.
                                                                       get('product_id')).mapped('amended_quantity'))
            done_qty = sum(done_pickings.move_ids.filtered(lambda move: move.product_id.id == val.get('product_id')).mapped('product_uom_qty'))
            cancel_pickings = self.env['stock.picking'].search([('main_jobwork_id', '=', self.id),
                                                     ('origin', '=', f"Cancel/Main Job Work: {self.job_work_id.reference}")])
            if cancel_pickings:
                done_qty -= sum(cancel_pickings.filtered(lambda pick: pick.product_id.id == val.get('product_id')).mapped('product_uom_qty'))
            if full_cancel:
                val.update({'product_uom_qty': done_qty})
                new_vals.append(val)
            elif (total_qty - done_qty) - val.get('product_uom_qty') < 0:
                val.update({'product_uom_qty': abs((total_qty - done_qty) - val.get('product_uom_qty'))})
                new_vals.append(val)
        return new_vals
