from odoo import models, fields, api, _
from barcode import Code128
from barcode.writer import ImageWriter
import os, base64
from io import BytesIO
from odoo.exceptions import UserError


class MrpBarcode(models.Model):
    _name = 'mrp.barcode'
    _inherit = 'mail.thread'
    _description = 'Manage barcode for product in manufacturing order'

    @api.constrains('name')
    def _constrains_assignment_domain(self):
        for rec in self:
            if self.search_count([('name', '=', rec.name)]) > 2:
                raise UserError(_('This Barcode is already Exist.'))

    name = fields.Char()
    product_id = fields.Many2one(string='Product', comodel_name='product.product')
    design = fields.Char(readonly=1)
    size = fields.Char(compute='_compute_required_data', store=True)
    division_id = fields.Many2one("mrp.division", string="Division", related='product_id.product_tmpl_id.division_id')
    quality = fields.Char(compute='_compute_required_data', store=True)
    mrp_id = fields.Many2one(string='Manufacturing Order', comodel_name='mrp.production', tracking=True)
    main_job_work_id = fields.Many2one(string='Subcontractor Job Work', comodel_name='main.jobwork', tracking=True)
    state = fields.Selection(selection=[('1_draft', 'Draft'), ('2_allotment', 'Job Allotment'),
                                        ('3_allocated', 'Job Allocated'), ('4_received', 'Weaving Received'),
                                        ('5_verified', 'Weaving Completed'), ('6_rejected', 'Weaving Rejected'),
                                        ('7_finishing', 'Finishing'), ('8_done', "Manufacturing Done"),
                                        ('9_packaging', 'Packed'), ('10_done', 'Shipped'),('cancel', 'Cancelled')], tracking=True)
    barcode = fields.Binary()
    color = fields.Char(compute='_compute_required_data', store=True)
    company_id = fields.Many2one(comodel_name='res.company')
    is_downloaded = fields.Boolean(tracking=True)
    bazaar_id = fields.Many2one(comodel_name='main.baazar', tracking=True)
    sale_id = fields.Many2one(comodel_name="sale.order", string="Sale Order", tracking=True)
    process_finished = fields.Many2many(comodel_name='mrp.workorder',  tracking=True)
    current_process = fields.Many2one(comodel_name="mrp.workorder",  tracking=True)
    current_workcenter = fields.Many2one(comodel_name='mrp.workcenter', related='current_process.workcenter_id', store=True)
    next_process = fields.Many2one(comodel_name='mrp.workorder',  tracking=True)
    location_id = fields.Many2one(comodel_name='stock.location', string="Current Location", tracking=True)
    finishing_size = fields.Float(related="product_id.finishing_area", string="Area")
    pen_inc_ids = fields.One2many(comodel_name='inno.incentive.penalty', inverse_name='barcode_id')
    is_mrp_done = fields.Boolean()

    @api.depends('product_id')
    def _compute_required_data(self):
        for rec in self:
            size = rec.product_id.product_template_attribute_value_ids.filtered(lambda al: al.attribute_id.name in ['size', 'Size'])
            if size.__len__() > 1:
                raise UserError(_("Found more that one size in the product.\n"
                                  "Please check the product and configure it correctly."))
            rec.write({'size': size[0].name if size else 'N/A',
                       'color': rec.product_id.product_tmpl_id.color.name if rec.product_id.product_tmpl_id.color
                       else 'N/A',
                       'quality': rec.product_id.product_tmpl_id.quality.name if rec.product_id.product_tmpl_id.quality
                       else 'N/A'})

    def generate_barcode(self):
        """
        Generates Barcode
        """
        for rec in self:
            svg_img_bytes = BytesIO()
            Code128(rec.name, writer=ImageWriter()).write(svg_img_bytes)
            rec.barcode = base64.b64encode(svg_img_bytes.getvalue())

    def move_barcode_inventory(self):
        for rec in self:
            mrp_id = rec.mrp_id
            if mrp_id != 'done' and not rec.is_mrp_done:
                rec.is_mrp_done = True
                ready_moves = mrp_id.move_finished_ids.filtered(
                    lambda m: m.product_id == mrp_id.product_id and m.state not in ('done', 'cancel'))
                if mrp_id.final_qty_done == (mrp_id.product_uom_qty - 1):
                    ready_moves.write({'quantity_done': 1, 'location_dest_id': rec.location_id.id})
                    ready_moves._action_done()
                else:
                    ready_moves.write({'quantity_done': 1, 'location_dest_id': rec.location_id.id})
                    ready_moves._action_done(cancel_backorder=False)
                mrp_id.final_qty_done += 1
                if mrp_id.final_qty_done == mrp_id.product_uom_qty:
                    mrp_id.state = 'done'
