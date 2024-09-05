from odoo import fields, models, _,api
from odoo.exceptions import UserError

    
class MrpQualityControl(models.Model):
    _name = 'mrp.quality.control'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Quality Control'
    
    name = fields.Char('Reference', default=lambda self: _('New'))
    subcontractor_id = fields.Many2one('res.partner', string='Subcontractors')
    qc_manager_id = fields.Many2one('res.partner', string="QC Manager")
    quality_state = fields.Selection([('draft', 'To do'), ('pass', 'Passed'), ('fail', 'Failed')], string='Status',
                                     default='draft', tracking=True)
    user_id = fields.Many2one('res.users', 'Responsible')
    note = fields.Text('Notes')
    picture = fields.Many2many('ir.attachment', string="Image")
    main_job_work_id = fields.Many2one("main.jobwork", string="Main Job Work")
    job_work_ids = fields.Many2many(comodel_name='mrp.job.work')
    division_id = fields.Many2one(related='main_job_work_id.division_id')

    def do_quality_check(self):
        """
        Will process the Qc either pass of Fail
        """
        if not self.picture:
            raise UserError(_("Please Capture some picture for the proof."))
        self.quality_state = self._context.get('qc')

    def open_loom_inspection_view(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Loom Inspection"),
            'view_mode': 'form',
            'res_model': 'mrp.quality.control',
            'res_id': self.id
        }
