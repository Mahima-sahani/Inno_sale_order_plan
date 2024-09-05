from odoo import fields, models, _, api
from odoo.exceptions import UserError


class MainJobwork(models.Model):
    _inherit = "main.jobwork"
    
    branch_id = fields.Many2one("weaving.branch", string="Branch")
    parent_job_work_id = fields.Many2one(comodel_name='main.jobwork')
    child_job_work_ids = fields.One2many(comodel_name='main.jobwork', inverse_name='parent_job_work_id')
    is_branch_subcontracting = fields.Boolean()
    weaving_center_name = fields.Char()

    def create_sequence(self):
        for rec in self:
            seq = False
            if rec.branch_id:
                if rec.branch_id.name == 'W.C.CHAKSARI':
                    seq = self.env['ir.sequence'].next_by_code('main.jobwork.chk')
                elif rec.branch_id.name == 'W.C.SARVATKHANI':
                    seq = self.env['ir.sequence'].next_by_code('main.jobwork.srv')
                elif rec.branch_id.name == 'W.C.FATTUPUR':
                    seq = self.env['ir.sequence'].next_by_code('main.jobwork.ftpp')
                elif rec.branch_id.name == 'W.C.FATTUPUR':
                    seq = self.env['ir.sequence'].next_by_code('main.jobwork.ftpp')
                elif rec.branch_id.name == 'MAHARAJGANJ':
                    seq = self.env['ir.sequence'].next_by_code('main.jobwork.mhrj')
            else:
                if rec.division_id.name == 'TUFTED':
                    hl = [rec for rec in rec.jobwork_line_ids.product_id.product_tmpl_id.construction.mapped('name') if
                          rec in ['HAND LOOMED', 'HANDLOOM']]
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


    def button_confirm(self):
        super().button_confirm()
        if self.branch_id:
            self.issue_job_work()

    def button_cancel_for_branch(self):
        return {
            'name': _(f"Cancel Job Work {self.reference}"),
            'view_mode': 'form',
            'res_model': 'inno.cancel.job.work',
            'context': {'default_job_work_id': self.id, 'default_branch_allocation': True},
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    def button_done_job_work(self):
        if self.branch_id:
            if not self.quantity_full_received:
                raise UserError(_("All Products should be received before completing the job work."))
            raw_material_group = ['yarn', 'wool', 'acrlicy_yarn', 'jute_yarn', 'polyster_yarn', 'wool_viscose_blend', ]
            pending_mat = []
            # Add the pending Material to the Weaving Center's Account
            for materials in self.alloted_material_ids.filtered(
                    lambda jw: jw.product_id.product_tmpl_id.raw_material_group in raw_material_group):
                pending_qty = (materials.alloted_quantity + materials.amended_quantity) - materials.returned_quantity
                if pending_qty > 0.0:
                    pending_mat.append({'product_id': materials.product_id.id, 'quantity': pending_qty})
            if pending_mat:
                pending_record = self.env['inno.pending.material'].search([
                    ('subcontractor_id', '=', self.subcontractor_id.id),
                    ('Weaving_center_id', '=',  self.branch_id.id)], limit=1)
                if not pending_record:
                    pending_record = self.env['inno.pending.material'].create({
                        'subcontractor_id': self.subcontractor_id.id, 'Weaving_center_id':  self.branch_id.id})
                for mat in pending_mat:
                    pending_line = pending_record.material_line_ids.filtered(
                        lambda ml: ml.product_id.id == mat.get('product_id'), limit=1)
                    if pending_line:
                        pending_line.quantity += mat.get('quantity')
                    else:
                        pending_record.write({'material_line_ids': [(0, 0, {'product_id': mat.get('product_id'),
                                                                            'quantity': mat.get('quantity')})]})
            self.state = 'done'
        else:
            super().button_done_job_work()
