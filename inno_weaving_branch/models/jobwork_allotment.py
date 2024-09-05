from odoo import fields, models, _, api
from datetime import date
from odoo.exceptions import UserError, ValidationError, MissingError
import logging
_logger = logging.getLogger(__name__)



class JobworkAllotment(models.Model):
    _name = "jobwork.allotment"
    _description = 'Jobwork Allotment'
    _inherit = ['mail.thread','mail.activity.mixin']
    _rec_name = "branch_id"
    
    branch_id = fields.Many2one("weaving.branch", string="Branch")
    design_product_id = fields.Many2one(related="work_order_id.production_bom_id", string="Design")
    product_id = fields.Many2one(related="work_order_id.product_id", string="Product")
    product_image = fields.Image(related="product_id.image_1920")
    product_qty = fields.Integer("Original Quantity")
    alloted_product_qty = fields.Integer("Alloted Quantity")
    remaining_product_qty = fields.Integer("Remaining Quantity", tracking=True, compute='_compute_remaining_qty', store=True)
    issue_date = fields.Date(string='Issued Date', default=fields.Datetime.today())
    expected_received_date = fields.Date(string='Expected Date')
    division_id = fields.Many2one(related="work_order_id.division_id", store=True, string='Division')
    mrp_area = fields.Float(related="product_id.mrp_area", string="Area", readonly="1")
    allotment = fields.Selection([
        ('to_do', 'To Do'),
        ('partial', 'Partially Alloted'),
        ('full', 'Fully Alloted'),
        ], string='Status', default='to_do', tracking=True, compute='compute_allotment', store=True)
    work_order_id = fields.Many2one("mrp.workorder", "Work Order")
    operation_id = fields.Many2one(related='work_order_id.workcenter_id', string="Operation")
    mo_order_id = fields.Many2one(related="work_order_id.production_id", string="Manufacturing Order")
    sale_order_id = fields.Many2one(string="Sale Order", comodel_name='sale.order', compute="compute_required_details", store=True)
    jobwork_id = fields.Many2one("main.jobwork", string="Main Job")
    barcodes = fields.Many2many(string='Allotted Lots', comodel_name='mrp.barcode')
    color = fields.Integer(compute='compute_kanban_color', default=4)
    delivery_id = fields.Many2one(comodel_name='stock.picking')
    alloted_jobwork_ids = fields.One2many(comodel_name="mrp.job.work", inverse_name="allotment_id")

    @api.depends('alloted_jobwork_ids')
    def _compute_remaining_qty(self):
        for rec in self:
            # by hi man
            # alloted_qty = self.barcodes.filtered(lambda bcode: bcode.state == '3_allocated').__len__()
            #by shiv
            alloted_qty = rec.barcodes.filtered(lambda bcode: bcode.branch_main_job_work_id and bcode.main_job_work_id).__len__()
            # alloted_qty=(self.barcodes.filtered(lambda br: rec.alloted_jobwork_ids.main_jobwork_id.id in br.main_job_work_id.ids))
            rec.write({
                'alloted_product_qty': alloted_qty,
                'remaining_product_qty': rec.product_qty - alloted_qty
            })

    @api.depends('remaining_product_qty')
    def compute_allotment(self):
        for rec in self:
            if rec.remaining_product_qty == rec.product_qty:
                rec.allotment = 'to_do'
            elif rec.remaining_product_qty == 0:
                rec.allotment = 'full'
            else:
                rec.allotment = 'partial'

    def compute_kanban_color(self):
        for rec in self:
            rec.color = 4 if rec.allotment == 'to_do' else 2 if rec.allotment == 'partial' else 10

    @api.depends('work_order_id')
    def compute_required_details(self):
        for rec in self:
            rec.sale_order_id = rec.work_order_id.production_id.procurement_group_id.\
                                    mrp_production_ids.move_dest_ids.group_id.sale_id.id or False

    def create(self, vals):
        res = super(JobworkAllotment, self).create(vals)
        _logger.info("~~~~~~~res1~~~sss~~%r~~~~~~~~",res)
        for job_allotment in res:
            job_allotment.remaining_product_qty = job_allotment.product_qty
        return res
    
    def map_job_work_allotement_order_record(self):
        if self.jobwork_id.ids.__len__() > 1:
            raise UserError(_("you Can't Allot job allotment with different main job works"))
        not_delivered = self.env['stock.picking'].search_count([('main_jobwork_id', '=', self.jobwork_id.id),
                                                                ('origin', '=', self.jobwork_id.reference),
                                                                ('state', '!=', 'done')])
        if not_delivered:
            raise UserError(_(f"Delivery : {not_delivered.name} is not "
                              f"Validated related to Job work : {self.jobwork_id.reference}"))
        return {
                'type': 'ir.actions.act_window',
                'name': _("Weaving Center Allotment"),
                'view_mode': 'form',
                'res_model': 'weaving.center.allotment',
                "target": "new",
            }
