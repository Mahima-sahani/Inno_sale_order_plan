import json
from email.utils import format_datetime
from odoo import fields, models, _, api
from datetime import datetime, timedelta
from odoo.exceptions import UserError

import logging

_logger = logging.getLogger(__name__)


class MrpWorkOrder(models.Model):
    _inherit = 'mrp.workorder'

    main_job_work_id = fields.Many2one("main.jobwork", "Main Job Work")
    total_duration = fields.Integer(string="Total Duration", default=0.0)
    manager_id = fields.Many2one('res.partner', string='Manager')
    division_id = fields.Many2one(related="product_id.product_tmpl_id.division_id", store=True, string='Division')
    allotted_qty = fields.Float("Allotted Qty", compute='_compute_product_wo_qty')
    remaining_qty = fields.Float(string="Remaining", compute='_compute_product_wo_qty')
    finished_qty = fields.Float(string="Finished Qty", copy=False)
    parent_id = fields.Many2one(comodel_name='mrp.workorder')
    remaining_to_allocate = fields.Float(string="Allocation Remaining")
    sale_id = fields.Many2one(comodel_name='sale.order', store=True, compute='compute_sale_id')
    allotment = fields.Selection([
        ('to_do', 'To Do'),
        ('partial', 'Partially Alloted'),
        ('full', 'Fully Alloted'),
    ], store=True, string='Status', default='to_do', tracking=True, compute='_compute_allotment_status')
    product_tmpl_id = fields.Many2one(related='product_id.product_tmpl_id', store=True)
    sale_order_date = fields.Datetime(related='sale_id.date_order')
    sale_expected_date = fields.Date(related='sale_id.validity_date')
    quality = fields.Many2one(related="product_id.product_tmpl_id.quality", string="Quality")
    alloted_area = fields.Float("Allotted Area", compute='_compute_area_qty')
    remaining_area = fields.Float(string="Remaining Area", compute='_compute_area_qty')

    @api.depends('allotted_qty','remaining_to_allocate')
    def _compute_area_qty(self):
        for rec in self:
            rec.write({'alloted_area': round(rec.product_id.mrp_area * rec.allotted_qty,
                                             0) if rec.allotted_qty > 0.00 else 0.00,
                       'remaining_area': round(rec.product_id.mrp_area * rec.remaining_to_allocate,
                                               0) if rec.remaining_to_allocate > 0.00 else 0.00})

    # def unlink(self):
    #     for rec in self:
    #         if rec.finished_qty > 0:
    #             raise UserError(_("This Workorder Can't Be deleted\n"
    #                               "This Operation is already finished in some barcodes."))
    #         if self.env['mrp.barcode'].search_count([('current_process', '=', rec.id)]):
    #             raise UserError(_("This Workorder can't be deleted\n"
    #                               "This Operation is in process for some barcodes"))
    #         rec.production_id.product_tmpl_id.bom_ids.operation_ids.filtered(
    #             lambda opr: opr.workcenter_id.id == rec.operation_id.workcenter_id.id).unlink()
    #         parent = rec.parent_id
    #         next_process = self.env['mrp.workorder'].search([('parent_id', '=', rec.id)])
    #         next_process.parent_id = parent.id
    #         barcodes_to_skip_process = self.env['mrp.barcode'].search([('next_process', '=', rec.id)])
    #         barcodes_to_skip_process.write({'next_process': next_process.id})
    #         for barcode in barcodes_to_skip_process:
    #             barcode.message_post(body=f"<b>{rec.name} Process is skipped</b><br/>"
    #                                       f"As the Workorder related to this operation is deleted. <br/>"
    #                                       f"Next process will be updated to <b>{next_process.name}</b>")
    #     super().unlink()

    @api.depends('production_id')
    def compute_sale_id(self):
        for rec in self:
            try:
                rec.sale_id = rec.production_id.move_dest_ids.group_id.sale_id.id
            except Exception:
                rec.sale_id = False

    def update_qty(self):
        lines = self.env['mrp.workorder'].search([])
        for rec in lines:
            rec._compute_allotment_status()

    @api.depends('remaining_qty', 'allotted_qty')
    def _compute_allotment_status(self):
        for rec in self:
            # barcodes =self.env['mrp.barcode'].search([('mrp_id', '=', rec.production_id.id)])
            # fltt=barcodes.filtered(
            #     lambda bcode: bcode.current_process.id == rec.id or rec.id in bcode.process_finished.ids)
            # barcodes.filtered(lambda be: be.id not in fltt.ids)
            qty_in_production = len(self.env['mrp.barcode'].search([('mrp_id', '=', rec.production_id.id)]).
                                    filtered(lambda bcode: bcode.current_process.id == rec.id
                                                           or rec.id in bcode.process_finished.ids))
            rec.remaining_to_allocate = rec.allotted_qty - qty_in_production
            if qty_in_production == 0:
                rec.allotment = 'to_do'
            elif rec.allotted_qty == qty_in_production:
                rec.allotment = 'full'
            elif rec.allotted_qty > qty_in_production:
                rec.allotment = 'partial'

    @api.depends('finished_qty', 'allotted_qty')
    def _compute_product_wo_qty(self):
        for rec in self:
            if not rec.parent_id:
                allotted_qty = rec.qty_production
            else:
                allotted_qty = rec.parent_id.finished_qty
            rec.write({'allotted_qty': allotted_qty, 'remaining_qty': allotted_qty - rec.finished_qty})
            if rec.finished_qty == rec.qty_production and rec.state not in ['done',
                                                                            'cancel'] and rec.production_id.state != 'draft':
                rec.button_finish()

    def button_start(self):
        for rec in self:
            if not rec.allotted_qty:
                raise UserError(_("There is no quantity allotted to this process.\n"
                                  "Reason for this warning could be because there is no quantity "
                                  "finished in previous work order."))
            else:
                super().button_start()

    def _plan_workorder(self, replan=False):
        self.ensure_one()
        # Plan workorder after its predecessors
        start_date = max(self.production_id.date_planned_start, datetime.now())
        for workorder in self.blocked_by_workorder_ids:
            if workorder.state in ['done', 'cancel']:
                continue
            workorder._plan_workorder(replan)
            if workorder.date_planned_finished:
                start_date = max(start_date, workorder.date_planned_finished)
        # Plan only suitable workorders
        if self.state not in ['pending', 'waiting', 'ready']:
            return
        if self.leave_id:
            if replan:
                self.leave_id.unlink()
            else:
                return
        # Consider workcenter and alternatives
        workcenters = self.workcenter_id | self.workcenter_id.alternative_workcenter_ids
        best_finished_date = datetime.max
        vals = {}
        for workcenter in workcenters:
            # Compute theoretical duration
            if self.workcenter_id == workcenter:
                duration_expected = self.duration_expected
            else:
                duration_expected = self._get_duration_expected(alternative_workcenter=workcenter)
            from_date, to_date = workcenter._get_first_available_slot(start_date, duration_expected)
            # If the workcenter is unavailable, try planning on the next one
            if not from_date:
                continue
            # Check if this workcenter is better than the previous ones
            if to_date and to_date < best_finished_date:
                best_start_date = from_date
                best_finished_date = to_date
                best_workcenter = workcenter
                vals = {
                    'workcenter_id': workcenter.id,
                    'duration_expected': duration_expected,
                }
        # If none of the workcenter are available, raise
        # if best_finished_date == datetime.max:
        #     raise UserError(_('Impossible to plan the workorder. Please check the workcenter availabilities.'))
        # Create leave on chosen workcenter calendar
        # leave = self.env['resource.calendar.leaves'].create({
        #     'name': self.display_name,
        #     'calendar_id': best_workcenter.resource_calendar_id.id,
        #     'date_from': best_start_date,
        #     'date_to': best_finished_date,
        #     'resource_id': best_workcenter.resource_id.id,
        #     'time_type': 'other'
        # })
        # vals['leave_id'] = leave.id
        self.write(vals)
