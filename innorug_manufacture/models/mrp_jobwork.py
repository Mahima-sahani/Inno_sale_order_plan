from odoo import fields, models, _,api
from datetime import datetime, timedelta
from odoo.exceptions import UserError

class MrpJobWork(models.Model):
    _name = "mrp.job.work"
    _description = 'Job Work'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char(string='Order Reference')
    product_qty = fields.Float(string="Quantity")
    received_qty = fields.Float("Received Quantity", tracking=True)
    mrp_work_order_id = fields.Many2one(comodel_name="mrp.workorder", string="Work Order")
    main_jobwork_id = fields.Many2one("main.jobwork", string="Main Job Work")
    product_id = fields.Many2one(comodel_name='product.product', string="Product_id")
    subcontractor_id = fields.Many2one(related='main_jobwork_id.subcontractor_id', store=True)
    issue_date = fields.Date()
    barcodes = fields.Many2many(comodel_name='mrp.barcode')
    division_id = fields.Many2one(related="product_id.division_id", store=True, string='Division')
    total_weight = fields.Float("Total Weight")
    design = fields.Char(related="product_id.product_tmpl_id.name", string="Design", readonly="1")
    mrp_area = fields.Float(related="product_id.mrp_area", string="Area", readonly="1")
    area = fields.Float(string="Area", readonly="1", compute='_compute_area_by_size', store=True)
    # size = fields.Char( string="Product Size Name", related="product_id.mrp_size", readonly="1")
    inno_mrp_size_id = fields.Many2one(string="Product Size Name", related="product_id.inno_mrp_size_id", readonly="1")
    total_area = fields.Float("Area", compute='_compute_area_by_size', store=True, digits=(10, 3))
    rate = fields.Float(digits=(10, 3))
    rate_discount = fields.Float(digits=(10, 3))
    original_rate = fields.Float(digits=(10, 3))
    return_quantity = fields.Float(digits=(10, 3))
    uom_id = fields.Many2one(comodel_name='uom.uom', string="Unit Of Measure")
    incentive = fields.Float(digits=(10, 3), string='Incentive')

    @api.depends('inno_mrp_size_id', 'uom_id')
    def _compute_area_by_size(self):
        for rec in self:
            if not rec.uom_id:
                rec.uom_id = 27
            area = rec.product_id.inno_mrp_size_id.area_sq_yard \
                if rec.uom_id.id == 27 else rec.product_id.inno_mrp_size_id.area if rec.uom_id.id == 21 \
                else rec.product_id.inno_mrp_size_id.area_sq_mt \
                if rec.uom_id.id == 9 else rec.product_qty if rec.uom_id.id == 1 else 0
            rec.write({'area': area, 'total_area': area if rec.uom_id == 1 else area * rec.product_qty})

    def update_rate(self):
        if self.mrp_work_order_id.sale_id:
            raise UserError(_("only sample rate can be updated."))
        return {
            'name': "Update Sample Rate",
            'view_mode': 'form',
            'res_model': 'sample.rate.update',
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    @api.onchange('rate_discount')
    def _compute_field_type(self):
        if self.rate_discount < 0:
            raise UserError(_("Rate discount can't be negative."))
        if self.rate_discount >= self.original_rate:
            raise UserError(_("You can add discount more than the actual rate."))



class SubBomlines(models.Model):
    _name = "subcontractor.alloted.product"
    _description = "Subcontractor Alloted Products"

    product_id = fields.Many2one(comodel_name="product.product", string="Product", readonly="1")
    alloted_quantity = fields.Float(string="Alloted Quantity", readonly="1", digits=(12, 4))
    quantity_released = fields.Float(string='Quantity Released', readonly="1", digits=(12, 4))
    amended_quantity = fields.Float(string="Amended Qty", digits=(12, 4))
    returned_quantity = fields.Float(string="Returned Quantity", digits=(12, 4))
    pending_qty = fields.Float(string="Pending Quantity", digits=(12, 4))
    adjusted_qty = fields.Float(string="Adjusted Quantity", digits=(12, 4))
    product_uom = fields.Many2one(comodel_name="uom.uom", string="UOM")
    main_job_work_id = fields.Many2one(comodel_name="main.jobwork", string="Main Job Work")
    add_pending_qty = fields.Boolean(string='Use Pending Qty')
    location_id = fields.Many2one("stock.location", string="Location",
                                  default=lambda self: self.env.user.material_location_id.id,
                                  domain=[('usage', '=', 'internal')])
    old_balance = fields.Float(digits=(12, 4))
