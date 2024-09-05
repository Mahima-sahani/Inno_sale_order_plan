from odoo import models, fields, api, _
from odoo.exceptions import UserError


class UpdateExpectedDate(models.TransientModel):
    _name = 'inno.update.expected.date'
    _description = "update Expected Date"

    job_work_id = fields.Many2one(comodel_name='main.jobwork')
    orignal_expected_date = fields.Date(related='job_work_id.expected_received_date')
    new_expected_date = fields.Date()
    reason = fields.Char()

    def do_update(self):
        remaining_days_to_add = (self.new_expected_date - self.orignal_expected_date).days
        self.job_work_id.write({'expected_received_date': self.new_expected_date,
                                'remaining_days': self.job_work_id.remaining_days + remaining_days_to_add})
        self.job_work_id.message_post(body=f"<b>Updated Expected Date:</b><br/> {self.orignal_expected_date} -> "
                                      f"{self.new_expected_date}<br/><b>Reason:</b><br/> {self.reason}")

    @api.onchange('new_expected_date')
    def onchange_expected_date(self):
        if self.new_expected_date:
            if self.new_expected_date < self.orignal_expected_date:
                raise UserError(_("You Can't set older dates than Orignal date"))

