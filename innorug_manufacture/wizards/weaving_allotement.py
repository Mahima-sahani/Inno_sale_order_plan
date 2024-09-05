from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, MissingError
from datetime import datetime, timedelta


class MrpWeaving(models.TransientModel):
    _name = 'mrp.weaving.wizards'

    def get_subcontractor_domain(self):
        weaving_id = self.env['inno.config'].sudo().search([]).weaving_operation_id.id
        if weaving_id:
            query = f'select res_partner_id from res_partner_workcenter_rel where mrp_workcenter_id = {weaving_id}'
            self._cr.execute(query)
            return [('id', 'in', [row[0] for row in self._cr.fetchall()])]
        else:
            return [('id', 'in', [])]

    issue_date = fields.Date(string='Issue Date', default=fields.Date.today())
    expected_date = fields.Date("Expected Date")
    weaving_order_line = fields.One2many("mrp.weaving.wizards.line", "weaving_order_id", string="Weaving Order")
    subcontractor_id = fields.Many2one(comodel_name='res.partner', string='Subcontractor',
                                       domain=get_subcontractor_domain)
    allotment_type = fields.Selection(selection=[('subcontractor', 'Subcontractor')])
    alloted_days = fields.Integer()
    is_sunday = fields.Boolean()
    is_full_finish = fields.Boolean(string='Is Full Finish Order?')
    is_far = fields.Boolean(string='Is Direct Delivery?')

    @api.onchange('alloted_days')
    def onchange_alloted_days(self):
        if self.alloted_days < 0:
            raise UserError(_("You can't enter negative value."))
        if not self.issue_date:
            self.issue_date = datetime.now()
        if self.alloted_days > 0:
            self.expected_date = datetime.strptime(str(self.issue_date), "%Y-%m-%d") + timedelta(
                days=self.alloted_days)
        else:
            self.expected_date = False

    @api.onchange('expected_date')
    def onchange_expected_date(self):
        if self.expected_date:
            if self.expected_date < self.issue_date:
                raise UserError(_("You Can't set older dates than issue date"))
            self.alloted_days = (self.expected_date - self.issue_date).days
            self.is_sunday = True if self.expected_date.weekday() == 6 else False
        else:
            self.is_sunday = False

    @api.model
    def default_get(self, fields_list):
        work_orders = self.env['mrp.workorder'].browse(self._context.get('active_ids'))
        wo_without_sale = work_orders.filtered(lambda wo: not wo.sale_id)
        # sale_id_len = work_orders.sale_id.ids.__len__()
        # if (sale_id_len == 1 and wo_without_sale) or sale_id_len > 1:
        #     raise UserError(_("You can't allot work orders with different sale orders."))
        res = super().default_get(fields_list)
        vals = [(0, 0, {'product_id': rec.product_id.id, 'operation_id': rec.workcenter_id.id,
                        'production_id': rec.production_id.id, 'product_qty': rec.remaining_to_allocate,
                        'work_order_id': rec.id, 'product_price': rec.product_id.sudo().calculate_product_rate(rec.workcenter_id)})
                for rec in work_orders]
        res.update({'weaving_order_line': vals, 'allotment_type': self._context.get('allotment_type')})
        return res

    def do_confirm(self):
        self.confirm_mrp_and_start_wo()
        jobwork_vals = self.create_job_work_record()
        job_work = False
        if jobwork_vals:
            job_work = self.env['main.jobwork'].sudo().create(jobwork_vals)
            for rec in self.weaving_order_line:
                bcodes = self.update_barcode_data(job_work, rec)
                job = job_work.jobwork_line_ids.filtered(lambda jw: jw.mrp_work_order_id.id == rec.work_order_id.id)
                job.barcodes = bcodes.ids
        if job_work:
            job_work.create_sequence()
            return {
                'type': 'ir.actions.act_window',
                'name': _("Main Job Work"),
                'view_mode': 'form',
                'res_model': 'main.jobwork',
                'res_id': job_work.id,
                "target": "current",
            }
        else:
            raise UserError(_('Please Verify Quantity in your products line.'))

    def confirm_mrp_and_start_wo(self):
        for weaving_line in self.weaving_order_line:
            mrp = weaving_line.production_id
            if mrp.state == 'draft':
                mrp.action_confirm()
                mrp.button_plan()
            workorder = weaving_line.work_order_id
            if workorder.state not in ['progress', 'done', 'cancel'] and not workorder.is_user_working:
                workorder.button_start()


    def update_barcode_data(self, job_work, rec):
        bcodes = self.env['mrp.barcode'].search([('mrp_id', '=', rec.production_id.id),
                                                 ('state', '=', '1_draft')], limit=rec.alloted_qty)
        if bcodes.__len__() < rec.alloted_qty:
            raise UserError(_('No barcodes available to allocate.'))
        bcodes.write({'state': '3_allocated', 'main_job_work_id': job_work.id,
                      'current_process': rec.work_order_id.id,
                      'next_process': self.env['mrp.workorder'].search([('parent_id', '=', rec.work_order_id.id)]).id})
        rec.work_order_id._compute_allotment_status()
        return bcodes

    def create_job_work_record(self):
        job_vals = False
        config = self.env['inno.config'].sudo().search([], limit=1)
        if not config.allowed_fragments:
            raise UserError(_("Please ask your admin to set default allowed bazaar fragments(Chunks)."))
        job_line_vals = [(0, 0, {"mrp_work_order_id": rec.work_order_id.id, 'issue_date': self.issue_date,
                                 "product_qty": rec.alloted_qty, "product_id": rec.product_id.id,
                                 "area": self.get_area(rec.product_id, rec.product_id.sudo().get_rate_list_uom(rec.work_order_id.workcenter_id), rec.alloted_qty),
                                 'uom_id': rec.product_id.sudo().get_rate_list_uom(rec.work_order_id.workcenter_id),
                                 "total_area": rec.product_id.mrp_area * rec.alloted_qty,
                                 'original_rate': rec.product_id.sudo().calculate_product_rate(rec.work_order_id.workcenter_id)})
                         for rec in self.weaving_order_line if rec.alloted_qty > 0]
        if job_line_vals:
            division = self.weaving_order_line.work_order_id.division_id
            extra_time = self.env['inno.config'].sudo().search([], limit=1).extra_time or 0
            job_vals = {'work_order_ids': self.weaving_order_line.work_order_id.ids, 'extra_time': extra_time,
                        'jobwork_line_ids': job_line_vals, 'subcontractor_id': self.subcontractor_id.id,
                        'operation_id': self.weaving_order_line.work_order_id.workcenter_id.id,
                        'issue_date': self.issue_date, 'expected_received_date': self.expected_date,
                        'is_full_finish': self.is_full_finish, 'is_far': self.is_far,
                        'allowed_chunks': config.allowed_fragments,
                        'division_id': division[0].id if division else False}
        return job_vals

    @staticmethod
    def get_area(product, atype, qty):
        return product.inno_mrp_size_id.area_sq_yard if atype == 27 else product.inno_mrp_size_id.area \
            if atype == 21 else product.inno_mrp_size_id.area_sq_mt if atype == 9 else qty if atype == 1 else 0

class MrpWeavingLine(models.TransientModel):
    _name = 'mrp.weaving.wizards.line'

    product_id = fields.Many2one("product.product", string="Product")
    area = fields.Float(string='Area', digits=(12, 4), compute='compute_product_area')
    product_qty = fields.Float("Quantity")
    alloted_qty = fields.Float("Allote Qty")
    operation_id = fields.Many2one("mrp.workcenter")
    production_id = fields.Many2one("mrp.production")
    work_order_id = fields.Many2one("mrp.workorder")
    weaving_order_id = fields.Many2one("mrp.weaving.wizards")
    product_price = fields.Float(digits=(8, 3), string='Rate')

    @api.depends('alloted_qty')
    def compute_product_area(self):
        for rec in self:
            rec.area = rec.product_id.mrp_area * rec.alloted_qty

    @api.onchange('alloted_qty')
    def onchange_allote_qty(self):
        if self.alloted_qty > self.product_qty:
            raise UserError(_("Can't allocate more qty than available."))
        if self.alloted_qty < 0:
            raise UserError(_("Can't allocate qty in Negative."))

