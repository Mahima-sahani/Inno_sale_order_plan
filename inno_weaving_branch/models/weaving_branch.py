from odoo import fields, models, _, api
from datetime import date
import logging
_logger = logging.getLogger(__name__)



class MrpBranch(models.Model):
    _name = "weaving.branch"
    _description = 'Branch'
    _inherit = ['mail.thread','mail.activity.mixin']
    
    name = fields.Char("Branch")
    jobwork_id = fields.Many2one("jobwork.allotment", string="Job Work")
    main_jobwork_id = fields.Many2one("main.jobwork", string="Job Work")
    warehouse_id = fields.Many2one(string='Warehouse_id', comodel_name='stock.warehouse')
    total_product_qty = fields.Integer("Product Qty", compute="_qty_count")
    total_alloted_qty = fields.Integer("Alloted Qty", compute="_qty_count")
    total_remaining_qty = fields.Integer("Remaining Qty", compute="_qty_count")
    total_receive_qty = fields.Integer("Received Qty", compute="_qty_count")
    total_pending_qty = fields.Integer("Pending Qty", compute="_qty_count")
    baazar_id = fields.Many2one("main.baazar", string= "Baazar")
    partner_id = fields.Many2one(comodel_name='res.partner')
    
    
    def _qty_count(self):
        for rec in self:
            barcodes = self.env['mrp.barcode'].search([('branch_id', '=', rec.id)])
            rec.total_product_qty = len(barcodes)
            rec.total_alloted_qty = len(barcodes.filtered(lambda bcode: bcode.state == '3_allocated'))
            rec.total_remaining_qty = rec.total_product_qty - rec.total_alloted_qty
            rec.total_receive_qty = len(barcodes.filtered(lambda bcode: bcode.state == '5_verified'))
            rec.total_pending_qty = rec.total_alloted_qty - rec.total_receive_qty
    
    def button_action_for_job_work(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Job Work"),
            'view_mode': 'tree,form',
            'res_model': 'mrp.job.work',
            "target" : "current",
            "domain" : [('branch_id', '=', self.id)]
        }
    
    def button_action_for_main_Job_work_record(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': _("Main Job Work"),
            'view_mode': 'list,form',
            'res_model': 'main.jobwork',
            "target" : "current",
            "domain" : [('branch_id', '=', self.id)]
        }

    
    def button_action_for_alloted_record(self):
         return {
            'type': 'ir.actions.act_window',
            'name': _("Job Work Allotement"),
            'view_mode': 'tree,form',
            'res_model': 'jobwork.allotment',
            "target" : "current",
            "domain" : [('branch_id', '=', self.id)]
        }

    def open_associated_barcodes(self):
        record = []
        if self._context.get('operation') == 'total_qty':
            record = self.env['mrp.barcode'].search([('branch_id', '=', self.id)])
        if self._context.get('operation') == 'alloted_qty':
            record = self.env['mrp.barcode'].search([('branch_id', '=', self.id),
                                                     ('state', '=', '3_allocated')])
        if self._context.get('operation') == 'remaining_qty':
            record = self.env['mrp.barcode'].search([('branch_id', '=', self.id),
                                                     ('state', '=', '2_allotment')])
        if self._context.get('operation') == 'received_qty':
            record = self.env['mrp.barcode'].search([('branch_id', '=', self.id),
                                                     ('state', '=', '5_verified')])
        if self._context.get('operation') == 'pending_qty':
            record = self.env['mrp.barcode'].search([('branch_id', '=', self.id),
                                                     ('state', 'in', ['3_allocated', '6_rejected', '4_received'])])
        action = {
            'name': _("Barcodes"),
            'view_mode': 'form',
            'res_model': 'mrp.barcode',
            'type': 'ir.actions.act_window',
        }
        if not record:
            return
        if len(record) > 1:
            action.update({'view_mode': 'tree,form', 'domain': [('id', '=', record.ids)]})
        else:
            action.update({'view_type': 'form', 'res_id': record[0].id})
        return action