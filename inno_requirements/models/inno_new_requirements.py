from odoo import models, fields, api, _


class InnoNewRequirements(models.Model):
    _name = 'inno.new.requirement'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'New Requirement'

    name = fields.Char(string='Requirement Reference', default='/')
    state = fields.Selection(selection=[('draft', 'New'), ('management', 'Management Verified'),
                                        ('technical', 'Technical Team Verified'), ('analysis', 'Analysis'),
                                        ('development', 'Development'), ('testing', 'Testing'),
                                        ('live', 'Live on Production'), ('cancel', 'Rejected'),
                                        ('done', 'Verified By User')], default='draft',
                             group_expand='_expand_groups', tracking=True)
    deadline = fields.Date(string='Deadline')
    attachment_id = fields.Many2many('ir.attachment', string="Attachment")
    requirement_description = fields.Text(string='Requirement Description')
    management_suggestion = fields.Text(string='Management Suggestion', tracking=True)

    @api.model
    def _expand_groups(self, states, domain, order):
        return ['draft', 'management', 'technical', 'analysis', 'development', 'testing', 'live', 'done', 'cancel']

    def not_verified(self):
        return {
            'name': _("Cancellation" if self._context.get('type') == 'cancel' else "Requirement Update"),
            'view_mode': 'form',
            'res_model': 'requirement.not.verified',
            'type': 'ir.actions.act_window',
            'target': 'new'
        }

    @api.model_create_multi
    def create(self, vals):
        vals[0].update({'name': self.env['ir.sequence'].next_by_code('inno_new_requirement')})
        return super(InnoNewRequirements, self.sudo()).create(vals)

    def do_verify(self):
        self.state = self._context.get('type')

