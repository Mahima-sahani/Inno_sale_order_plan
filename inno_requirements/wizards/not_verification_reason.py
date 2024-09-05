from odoo import models, fields, api


class NotVerified(models.TransientModel):
    _name = 'requirement.not.verified'
    _description = 'Reason for Requirement cancelled or not verified'

    reason = fields.Text(string='Reason')

    def do_confirm(self):
        requirement = self.env['inno.new.requirement'].browse(self._context.get('active_id'))
        if self._context.get('type') == 'cancel':
            requirement.message_post(body=f'<b>Cancellation Reason</b><br/>===========<br/>{self.reason}')
            requirement.state = 'cancel'
        else:
            requirement.message_post(body=f'<b>Need Changes</b><br/>==========<br/>{self.reason}')
            requirement.state = 'analysis'
