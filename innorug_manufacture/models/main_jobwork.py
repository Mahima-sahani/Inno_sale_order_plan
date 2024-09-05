import base64
from odoo import fields, models, _, api
from odoo.exceptions import UserError
from datetime import timedelta
from dateutil import relativedelta

class MainJobwork(models.Model):
    _name = "main.jobwork"
    _description = 'Main Job Work'
    _rec_name = "reference"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    
    reference = fields.Char("Reference")
    operation_id = fields.Many2one("mrp.workcenter", string="Operation")
    subcontractor_id = fields.Many2one('res.partner', string='Subcontractor',
                                       domain="[('operation_id', '=', operation_id)]", tracking=True)
    quality_manager_id = fields.Many2one('res.partner', string='Quality Manager')
    work_order_ids = fields.Many2many("mrp.workorder", string="Operation")
    cost_center = fields.Char()
    issue_date = fields.Date(string='Date Issued')
    expected_received_date = fields.Date(string='Expected Date')
    total_day = fields.Integer(string='Total', compute='compute_total_days')
    extra_time = fields.Integer(string='Extra time')
    remaining_days = fields.Integer()
    jobwork_line_ids = fields.One2many(comodel_name="mrp.job.work", inverse_name="main_jobwork_id",
                                       string="Job Work Lines", ondelete="cascade")
    alloted_material_ids = fields.One2many("subcontractor.alloted.product", "main_job_work_id", "Alloted Material",
                                           ondelete="cascade")
    main_jobwork_components_lines = fields.One2many(comodel_name="subcontractor.alloted.product",
                                                    inverse_name="main_job_work_id", string="Job Work Components_line",
                                                    ondelete ="cascade")
    quality_control_ids = fields.One2many("mrp.quality.control","main_job_work_id", string="Quality Control",
                                          ondelete ="cascade")
    baazar_lines_ids = fields.One2many(comodel_name="main.baazar", inverse_name="main_jobwork_id",
                                       string="Baazar Product", ondelete ="cascade")
    division_id = fields.Many2one("mrp.division", string='Division')
    company_id = fields.Many2one(comodel_name='res.company')
    state = fields.Selection([('draft', 'DRAFT'), ('allotment', 'WAITING RELEASE'), ('release', 'RELEASE'),
                              ('receiving', 'Receiving'), ('qa', 'PROCESS QC'), ('baazar', 'BAAZAR'),
                              ('done', 'JOB FINISHED'), ('return_waiting', 'WAITING FOR MATERAIL RETURN'),
                              ('cancel', 'CANCELLED')], string='Status', default='draft', tracking=True)
    delivery_count = fields.Integer(compute='compute_delivery_return')
    return_count = fields.Integer(compute='compute_delivery_return')
    barcode_released = fields.Boolean()
    product_allotment_ids = fields.One2many(comodel_name='subcontractor.alloted.product',
                                            inverse_name='main_job_work_id')
    force_qa_needed = fields.Boolean(compute='compute_force_qa')
    quantity_full_received = fields.Boolean(compute='_compute_full_received', store=True)
    cancel_picking_count = fields.Integer(compute='compute_delivery_return')
    bill_count = fields.Integer(compute='_compute_bills')
    cancelled_barcodes = fields.Many2many(comodel_name='mrp.barcode')
    sale_id = fields.Many2one(related='work_order_ids.sale_id', store=True)
    allowed_chunks = fields.Integer(string='Allowed Chunks')
    extra_chunks = fields.Integer(string='Extra Chunks', tracking=True)
    total_chunks = fields.Integer(string='Total Allowed Bazaar')
    is_pending_qty = fields.Boolean(compute='compute_pending_qty', store=True)
    time_incentive = fields.Float(string='Time Incentive')
    time_penalty = fields.Float(string='Time Penalty')
    parallel_order_number = fields.Char(string="Old Order Number")
    loss = fields.Float(string='Loss', digits=(4, 3))
    remarks = fields.Text("Remarks")
    is_full_finish = fields.Boolean()
    is_far = fields.Boolean()


    def create_sequence(self):
        for rec in self:
            seq = False
            if rec.division_id.name == 'TUFTED':
                hl = [rec for rec in rec.jobwork_line_ids.product_id.product_tmpl_id.construction.mapped('name') if rec in ['HAND LOOMED', 'HANDLOOM']]
                if rec.is_full_finish:
                    seq = self.env['ir.sequence'].next_by_code('main.jobwork.ff.tuft')
                elif hl:
                    seq = self.env['ir.sequence'].next_by_code('main.jobwork.hl')
                else:
                    seq = self.env['ir.sequence'].next_by_code('main.jobwork.tuft')
            elif rec.division_id.name == 'KELIM':
                if rec.is_full_finish:
                    seq = self.env['ir.sequence'].next_by_code('main.jobwork.ff.kelim')
                else:
                    seq = self.env['ir.sequence'].next_by_code('main.jobwork.klim')
            elif rec.division_id.name == 'KNOTTED':
                if rec.is_full_finish:
                    seq = self.env['ir.sequence'].next_by_code('main.jobwork.ff.knot')
                else:
                    seq = self.env['ir.sequence'].next_by_code('main.jobwork.knot')
            rec.reference = seq

    # def create(self, vals):
    #     records = super().create(vals)
    #     for rec in records:
    #         seq = False
    #         if rec.division_id.name == 'TUFTED':
    #             hl = [rec for rec in rec.jobwork_line_ids.product_id.product_tmpl_id.construction.mapped('name') if rec in ['HAND LOOMED', 'HANDLOOM']]
    #             if rec.is_full_finish:
    #                 seq = self.env['ir.sequence'].next_by_code('main.jobwork.ff.tuft')
    #             elif hl:
    #                 seq = self.env['ir.sequence'].next_by_code('main.jobwork.hl')
    #             else:
    #                 seq = self.env['ir.sequence'].next_by_code('main.jobwork.tuft')
    #         elif rec.division_id.name == 'KELIM':
    #             if rec.is_full_finish:
    #                 seq = self.env['ir.sequence'].next_by_code('main.jobwork.ff.kelim')
    #             else:
    #                 seq = self.env['ir.sequence'].next_by_code('main.jobwork.klim')
    #         elif rec.division_id.name == 'KNOTTED':
    #             if rec.is_full_finish:
    #                 seq = self.env['ir.sequence'].next_by_code('main.jobwork.ff.knot')
    #             else:
    #                 seq = self.env['ir.sequence'].next_by_code('main.jobwork.knot')
    #         rec.reference = seq
    #     return records

    @api.onchange('time_incentive')
    def onchange_time_incentive(self):
        config_id = self.env['inno.config'].sudo().search([], limit=1)
        if config_id.time_incentive < 0.0 or config_id.manager_time_incentive < 0.0:
            raise UserError(_("Please ask you Admin to set time incentives."))
        admin_group = self.env.ref('innorug_manufacture.group_inno_weaving_admin').id
        if self.time_incentive < 0.0:
            raise UserError(_("Time Incentive Can't be Negative"))
        if admin_group not in self.env.user.groups_id.ids:
            user_group = self.env.ref('innorug_manufacture.group_inno_weaving_user').id
            manager_group = self.env.ref('innorug_manufacture.group_inno_weaving_manager').id
            user_ids = self.env.user.groups_id.ids
            if manager_group in user_ids and self.time_incentive > config_id.manager_time_incentive:
                raise UserError(_(f"You are only allowed to permit time incentive till {config_id.manager_time_incentive}"
                                  f"\nPlease ask you admin to add time incentive in this JobWork."))
            if manager_group not in user_ids and user_group in user_ids and self.time_incentive > config_id.time_incentive:
                raise UserError(_(f"You are only allowed to permit time incentive till {config_id.time_incentive}"
                                  f"\nPlease ask you Manager to add time incentive in this JobWork."))

    @api.onchange('time_penalty')
    def onchange_time_penalty(self):
        config_id = self.env['inno.config'].sudo().search([], limit=1)
        if config_id.time_incentive < 0.0 or config_id.manager_time_incentive < 0.0:
            raise UserError(_("Please ask you Admin to set time incentives."))
        admin_group = self.env.ref('innorug_manufacture.group_inno_weaving_admin').id
        if self.time_penalty < 0.0:
            raise UserError(_("Time Incentive Can't be Negative"))
        if admin_group not in self.env.user.groups_id.ids:
            user_group = self.env.ref('innorug_manufacture.group_inno_weaving_user').id
            manager_group = self.env.ref('innorug_manufacture.group_inno_weaving_manager').id
            user_ids = self.env.user.groups_id.ids
            if manager_group in user_ids and self.time_penalty > config_id.manager_time_incentive:
                raise UserError(
                    _(f"You are only allowed to permit time incentive till {config_id.manager_time_incentive}"
                      f"\nPlease ask you admin to add time incentive in this JobWork."))
            if manager_group not in user_ids and user_group in user_ids and self.time_penalty > config_id.time_incentive:
                raise UserError(_(f"You are only allowed to permit time incentive till {config_id.time_incentive}"
                                  f"\nPlease ask you Manager to add time incentive in this JobWork."))

    def compute_pending_qty(self):
        for rec in self:
            rec.is_pending_qty = True if sum(rec.alloted_material_ids.mapped('pending_qty')) > 0.0 else False

    def update_expected_date(self):
        return {
            'name': "Update Expected Date",
            'view_mode': 'form',
            'res_model': 'inno.update.expected.date',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': {'default_job_work_id': self.id}
        }

    def _compute_bills(self):
        for rec in self:
            rec.bill_count = self.env['account.move'].sudo().search_count([('job_work_id', '=', self.id)])

    def open_vendor_bills(self):
        bills = self.env['account.move'].search([('job_work_id', '=', self.id)])
        action = {
            'name': _(f"Bill(s) for {self.reference}"),
            'view_mode': 'form',
            'res_model': 'account.move',
            'type': 'ir.actions.act_window',
        }
        if len(bills) > 1:
            action.update({'view_mode': 'tree,form', 'domain': [('id', 'in', bills.ids)]})
        else:
            action.update({'view_type': 'form', 'res_id': bills[0].id})
        return action

    @api.depends('jobwork_line_ids.received_qty')
    def _compute_full_received(self):
        for rec in self:
            total_to_produce = sum(rec.jobwork_line_ids.mapped('product_qty')) - sum(rec.jobwork_line_ids.
                                                                                     mapped('return_quantity'))
            rec.quantity_full_received = True if sum(rec.jobwork_line_ids.
                                                     mapped('received_qty')) == total_to_produce else False

    def open_allocated_barcodes(self):
        return{'name': _("Issued Barcodes"), 'view_mode': 'tree', 'res_model': 'mrp.barcode',
               'domain': [('id', '=', self.jobwork_line_ids.barcodes.filtered(lambda br: br.id not in self.cancelled_barcodes.ids).ids)], 'type': 'ir.actions.act_window',
               'context': {'group_by': 'product_id'}}

    @api.depends('quality_control_ids')
    def compute_force_qa(self):
        for rec in self:
            rec.force_qa_needed = True if rec.quality_control_ids.filtered(lambda qc: qc.quality_state == 'draft')\
                else False

    @api.depends('issue_date', 'expected_received_date')
    def compute_total_days(self):
        for rec in self:
            rec.total_day = (rec.expected_received_date - rec.issue_date).days if\
                rec.issue_date and rec.expected_received_date else 0

    def compute_delivery_return(self):
        for rec in self:
            deliveries = self.env['stock.picking'].search_count([('main_jobwork_id', '=', rec.id),
                                                                 ('origin', '=', f"Main Job Work: {self.reference}")])
            returns = self.env['stock.picking'].search_count([('main_jobwork_id', '=', rec.id),
                                                              ('origin', '=', f"Return/Main Job Work: {self.reference}"
                                                               )])
            cancel = self.env['stock.picking'].search_count([('main_jobwork_id', '=', self.id),
                                                             ('origin', '=', f"Cancel/Main Job Work: {self.reference}")])
            rec.cancel_picking_count = cancel or 0
            rec.delivery_count = deliveries or 0
            rec.return_count = returns or 0

    def button_confirm(self):
        if self.product_allotment_ids:
            raise UserError(_("You have already alloted the components"))
        allotment_vals = dict()
        for raw_moves in self.jobwork_line_ids.mrp_work_order_id.move_raw_ids:
            jobwork = self.jobwork_line_ids.filtered(lambda jwl: jwl.mrp_work_order_id.id == raw_moves.workorder_id.id)
            if raw_moves.product_id.id in allotment_vals.keys():
                existing_data = allotment_vals.get(raw_moves.product_id.id)
                existing_data.update({'alloted_quantity': existing_data.get('alloted_quantity') + (raw_moves.product_qty / raw_moves.workorder_id.qty_production) * jobwork.product_qty})
            else:
                allotment_vals[raw_moves.product_id.id] = {'product_id': raw_moves.product_id.id,
                                                           'alloted_quantity': (raw_moves.product_qty / raw_moves.workorder_id.qty_production) * jobwork.product_qty,
                                                           'product_uom': raw_moves.product_uom.id,
                                                           'pending_qty': self.check_pending_qty(raw_moves.product_id)}
        for job in self.jobwork_line_ids:
            job.rate = job.original_rate - job.rate_discount
        if self.extra_chunks < 0:
            raise UserError(_("Extra Chunk Can't Be Negative"))
        self.write(({'product_allotment_ids': [(0, 0, val) for val in allotment_vals.values()],
                     'remaining_days': self.total_day + self.extra_time, 'state': 'allotment',
                     'total_chunks': self.allowed_chunks + self.extra_chunks}))

    def check_pending_qty(self, product_id):
        pending_record = self.env['inno.pending.material'].search([
            ('subcontractor_id', '=', self.subcontractor_id.id)], limit=1)
        if pending_record:
            pending_line = pending_record.material_line_ids.filtered(lambda ml: ml.product_id.id == product_id.id)
            return pending_line.quantity if pending_line else 0.0
        return 0.0

    def button_release_components(self):
        for rec in self:
            rec.transfer_stock_to_subcontracter()
            rec.issue_job_work()
            if self.is_full_finish and self.is_far:
                rec.state = 'receiving'
            else:
                rec.state = 'release'

    def transfer_stock_to_subcontracter(self):
        for rec in self.product_allotment_ids:
            if not rec.location_id:
                raise UserError(_("Please set Material Location."))
        parent_loc = self.env['stock.location'].search([('name', '=', self.branch_id.warehouse_id.code)])
        branch_loc = self.env['stock.location'].search([('name', '=', "Stock"), ('location_id', '=', parent_loc.id)]).id
        for rec in self.product_allotment_ids.location_id:
            lines = self.product_allotment_ids.filtered(lambda id: id.location_id.id == rec.id)
            operation_type, destination_location = self.get_location_and_opoeration(rec)
            try:
                job_stock_move = self.prepare_job_stock_move(rec.id, destination_location,lines)
                vals = {
                    'name': operation_type.sequence_id.next_by_id(),
                    'partner_id': self.subcontractor_id.id,
                    'picking_type_id': operation_type.id,
                    'location_id': branch_loc if self.branch_id else rec.id,
                    'location_dest_id': destination_location,
                    'move_ids': job_stock_move,
                    'state': 'draft',
                    'main_jobwork_id': self.id,
                    'origin': f"Main Job Work: {self.reference}"
                }
                self.env['stock.picking'].sudo().create(vals)
            except Exception as ex:
                raise UserError(_(ex))

    def get_location_and_opoeration(self, rec):
        # if not self.env.user.material_location_id:
        #     raise UserError(_("Please Ask Your Admin to set your Material Location."))
        warehouse = rec.warehouse_id
        operation_type = warehouse.out_type_id
        # source_location = self.env.user.material_location_id.id
        dest_location = self.env['stock.location'].search([('usage', '=', 'supplier')], limit=1).id
        if self.is_branch_subcontracting:
            branch = self.env['weaving.branch'].search([('name', '=', self.weaving_center_name)])
            if branch.warehouse_id:
                parent_loc = self.env['stock.location'].search([('name', '=', branch.warehouse_id.code)])
                dest_location = self.env['stock.location'].search([('name', '=', "Stock"), ('location_id', '=', parent_loc.id)]).id
            else:
                raise UserError(_("Ask your admin to set branch Warhouse"))
        return operation_type, dest_location

    def prepare_job_stock_move(self, source_location, destination_location,lines):
        """
        Prepare the stock move line as per the component set in the selected operation
        """
        moves = []
        for component in lines:
            pending_qty, pending_line = self.check_pending_line_and_qty(component.product_id)
            if pending_qty <= 0.0 or not component.add_pending_qty:
                moves.append((0, 0, {'name': f"Transfer : {self.reference}", 'product_id': component.product_id.id,
                                      'product_uom_qty': component.alloted_quantity,
                                      'product_uom': component.product_uom.id, 'location_id': source_location,
                                      'location_dest_id': destination_location}))
            elif pending_qty >= component.alloted_quantity:
                pending_line.quantity -= component.alloted_quantity
                component.write({'pending_qty': (pending_qty - component.alloted_quantity), 'adjusted_qty': pending_qty})
            else:
                moves.append((0, 0, {'name': f"Transfer : {self.reference}", 'product_id': component.product_id.id,
                                      'product_uom_qty': component.alloted_quantity - pending_qty,
                                      'product_uom': component.product_uom.id, 'location_id': source_location,
                                      'location_dest_id': destination_location}))
                pending_line.quantity -= (component.alloted_quantity - pending_qty)
                component.write({'pending_qty': 0.0, 'adjusted_qty': pending_qty})
        return moves

    def check_pending_line_and_qty(self, product_id):
        pending_record = self.env['inno.pending.material'].search([
            ('subcontractor_id', '=', self.subcontractor_id.id)], limit=1)
        if pending_record:
            pending_line = pending_record.material_line_ids.filtered(
                lambda ml: ml.product_id.id == product_id.id)
            return pending_line.quantity, pending_line if pending_line else 0.0
        return 0.0, False

    def button_ready_bazaar(self):
        self.validate_pickings()
        if any(self.quality_control_ids.filtered(lambda qa: qa.quality_state == 'draft')):
            raise UserError(_("Please ask you Qa to complete the Quality process.\nor"
                              "\nYou can force done all the Qa in draft"))
        if self.baazar_lines_ids.filtered(lambda baz: baz.date.date() == fields.Datetime.today().date()):
            raise UserError(_("There is already a bazaar created for today."))
        self.env['main.baazar'].sudo().create({'main_jobwork_id': self.id, 'subcontractor_id': self.subcontractor_id.id,
                                        'state': 'receiving'})
        self.state = 'baazar'
    
    def button_force_qc(self):
        """
        Will forcefully pass the Qa process
        """
        self.quality_control_ids.filtered(lambda qa: qa.quality_state == 'draft').write({'quality_state': 'pass'})
    
    def button_amend_quantity(self):
        pickings = self.env['stock.picking'].search([('main_jobwork_id', '=', self.id),
                                                     ('origin', '=', f"Main Job Work: {self.reference}")])
        if pickings.filtered(lambda pick: pick.state == 'draft'):
            raise UserError(_("All Initial stock should be released first before Amending Quanity\n"
                              "Please ask inventory manager to validate the delivery order(s)."))
        return {
            'name': 'Need more Quantity',
            'view_mode': 'form',
            'res_model': 'inno.amend.return',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': "{'process': 'amend'}"
        }

    @staticmethod
    def button_return_components(self):
        return {
            'name': 'Return Consumables',
            'view_mode': 'form',
            'res_model': 'inno.amend.return',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': "{'process': 'return'}"
        }

    def button_done_job_work(self):
        """
        Done Job Work
        """
        if not self.quantity_full_received:
            raise UserError(_("All Products should be received before completing the job work."))
        raw_material_group = ['yarn', 'wool', 'acrlicy_yarn', 'jute_yarn', 'polyster_yarn', 'wool_viscose_blend',]
        pending_mat = []
        # Add the pending Material to the Subcontractor's Account
        for materials in self.alloted_material_ids.filtered(
                lambda jw: jw.product_id.product_tmpl_id.raw_material_group in raw_material_group):
            pending_qty = (materials.alloted_quantity + materials.amended_quantity) - materials.returned_quantity
            if pending_qty > 0.0:
                pending_mat.append({'product_id': materials.product_id.id, 'quantity': pending_qty})
        if pending_mat:
            pending_record = self.env['inno.pending.material'].search([
                ('subcontractor_id', '=', self.subcontractor_id.id)], limit=1)
            if not pending_record:
                pending_record = self.env['inno.pending.material'].create({
                    'subcontractor_id': self.subcontractor_id.id
                })
            for mat in pending_mat:
                pending_line = pending_record.material_line_ids.filtered(
                    lambda ml: ml.product_id.id == mat.get('product_id'))
                if pending_line:
                    pending_line.quantity += mat.get('quantity')
                else:
                    pending_record.write({'material_line_ids': [(0, 0, {'product_id': mat.get('product_id'),
                                                                        'quantity': mat.get('quantity')})]})
        # Add Time incentive in the Subcontractor's Account if all the products received in time.
        if self.remaining_days >= 0 and self.time_incentive > 0.0 and sum(self.jobwork_line_ids.mapped('return_quantity')) == 0:
            all_barcodes = self.jobwork_line_ids.barcodes.filtered(lambda bcode: bcode.main_job_work_id == self.id)
            total_area = sum([bcode.product_id.mrp_area for bcode in all_barcodes])
            self.env['inno.incentive.penalty'].create({
                'partner_id': self.subcontractor_id.id,
                'remark': f"Time Incentive for Job Work {self.reference}",
                'record_date': fields.Datetime.now(),
                'amount': total_area*self.time_incentive,
                'type': 'time_incentive'
            })
        self.state = 'done'

    def button_cancel(self):
        if self.env['stock.picking'].search_count([('main_jobwork_id', '=', self.id),
                                                   ('origin', '=', f"Cancel/Main Job Work: {self.reference}")]):
            if self.env['stock.picking'].search([('main_jobwork_id', '=', self.id),
                                                 ('origin', '=', f"Cancel/Main Job Work: "
                                                                 f"{self.reference}")]).state != 'done':
                raise UserError(_("Please Validate the Return Picking"))
            self.cancelation_process()
            return
        pickings = self.env['stock.picking'].search([('main_jobwork_id', '=', self.id),
                                                     ('origin', '=', f"Main Job Work: {self.reference}")])
        if self.state in ['draft', 'allotment']:
            self.cancelation_process()
        elif self.state == 'release' and not pickings.filtered(lambda pick: pick.state == 'done'):
            pickings.action_cancel()
            self.cancelation_process()
        elif self.state in ['baazar', 'qa'] or self.state == 'release' and pickings.filtered(lambda pick: pick.state == 'done'):
            return {
                'name': _(f"Cancel Job Work {self.reference}"),
                'view_mode': 'form',
                'res_model': 'inno.cancel.job.work',
                'context': {'default_job_work_id': self.id},
                'type': 'ir.actions.act_window',
                'target': 'new'
            }
        self.print_cancelled_barcodes()

    def print_cancelled_barcodes(self):
        report = self.env.ref('innorug_manufacture.action_report_job_work_cancellation',
                              raise_if_not_found=False).report_action(docids=self.id)
        return report

    def cancelation_process(self):
        self.state = 'cancel'
        barcodes = self.jobwork_line_ids.barcodes
        self.write({'cancelled_barcodes': [(4, bcode.id) for bcode in barcodes]})
        for barcode in barcodes:
            barcode.write({'state': '1_draft', 'main_job_work_id': False, 'current_process': False,
                           'next_process': barcode.current_process.id})

    def open_main_jobwork_delivery(self):
        """
        This method will open the stock.picking view of delivery order associated with main job work
        """
        record = self.env['stock.picking'].search([('main_jobwork_id', '=', self.id),
                                                   ('origin', '=', f"Main Job Work: {self.reference}")])
        return self.open_pickings(record, 'Delivery')

    def open_main_jobwork_return(self):
        """
        This method will open the stock.picking view of return order associated with main job work
        """
        record = self.env['stock.picking'].search([('main_jobwork_id', '=', self.id),
                                                   ('origin', '=', f"Return/Main Job Work: {self.reference}")])
        return self.open_pickings(record, 'Returns')

    def open_pickings(self, record, type):
        action = {
            'name': _(type),
            'view_mode': 'form',
            'res_model': 'stock.picking',
            'type': 'ir.actions.act_window',
        }
        if len(record) > 1:
            action.update({'view_mode': 'tree,form', 'domain': [('id', 'in', record.ids)]})
        else:
            action.update({'view_type': 'form', 'res_id': record[0].id})
        return action

    def open_cancel_return(self):
        picking_ids =self.env['stock.picking'].search([('main_jobwork_id', '=', self.id),
                                                        ('origin', '=', f"Cancel/Main Job Work: {self.reference}")])
        return {'name': "Job Work Cancellation", 'view_mode': 'tree,form', 'res_model': 'stock.picking',
                'type': 'ir.actions.act_window', 'domain': [('id', 'in', picking_ids.ids)]}

    def button_print_barcodes(self):
        """
        Will download the barcodes.
        """
        barcodes = self.jobwork_line_ids.barcodes
        if barcodes:
            if self.barcode_released and not self._context.get('regenerate'):
                penalty = self.env['inno.config'].sudo().search([], limit=1).barcode_reprint_penalty
                if not penalty:
                    raise UserError(_('Please ask you admin to Configure Barcode Penalties.'))
                return {
                    'name': 'Re-Generate Barcodes',
                    'view_mode': 'form',
                    'res_model': 'mrp.barcode.regenerate',
                    'context': {'barcodes': barcodes.ids},
                    'type': 'ir.actions.act_window',
                    'view_id': self.env.ref('innorug_manufacture.view_mrp_regenerate_barcode_wizard').id,
                    'target': 'new'
                }
            report = self.env.ref('innorug_manufacture.action_report_print_barcode',
                                  raise_if_not_found=False).report_action(docids=barcodes.ids)
            self.barcode_released = True
        return report

    def button_assign_qa(self):
        """
        Will verify the stock pickings and quality manager assigned to job work.
        """
        self.validate_pickings()
        if not self.quality_manager_id:
            raise UserError(_("Please Assign a Loom Inspector First!"))
        self.sudo().assign_qa_job()
        self.state = 'qa'

    def validate_pickings(self):
        if not self.barcode_released:
            raise UserError("Please Release Barcodes First")
        pickings = self.env['stock.picking'].search([('main_jobwork_id', '=', self.id),
                                                     ('origin', '=', f"Main Job Work: {self.reference}")])
        if self.is_pending_qty and sum(self.main_jobwork_components_lines.mapped('adjusted_qty')) > 0.0:
            return True
        if pickings and not pickings.filtered(lambda pick: pick.state == 'done'):
            raise UserError(_("Material is not released Yet.\n"
                              "Please ask inventory manager to validate the delivery order."))

    def assign_qa_job(self):
        """
        Generate a QC record for qc manager.
        """
        self.env['mrp.quality.control'].create({'name': f'QC for {self.reference}', 'main_job_work_id': self.id,
                                                'subcontractor_id': self.subcontractor_id.id,
                                                'qc_manager_id': self.quality_manager_id.id, 'quality_state': 'draft',
                                                'job_work_ids': self.jobwork_line_ids.ids})

    def issue_job_work(self):
        """
        Generate a job work sheet and attached it to chatter.
        """
        pdf = self.env.ref('innorug_manufacture.action_report_print_material_allocation',
                           raise_if_not_found=False).sudo()._render_qweb_pdf('innorug_manufacture.'
                                                                             'action_report_print_material_allocation',
                                                                             res_ids=self.id)[0]
        pdf = base64.b64encode(pdf).decode()
        attachment = self.env['ir.attachment'].create({'name': f"Weaving Job Work {self.reference}",
                                                       'type': 'binary', 'datas': pdf, 'res_model': 'main.jobwork',
                                                       'res_id': self.id,
                                                       })

    def update_remaining_days(self):
        today = fields.Datetime.today().date()
        jobworks_to_update = self.search([('quantity_full_received', '!=', True), ('remaining_days', '!=', 0),
                                          ('state', 'not in', ['done', 'cancel'])])
        for rec in jobworks_to_update:
            rec.remaining_days -= 1
