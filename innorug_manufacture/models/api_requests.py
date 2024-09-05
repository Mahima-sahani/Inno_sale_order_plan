
from odoo import models, fields, api


class ApiRequests(models.Model):
    _name = 'api.request'
    _description = "holds the record of api requests"
    _rec_name = 'request_reference'

    request_reference = fields.Char(string="Request Reference", default='/')
    user_id = fields.Many2one(comodel_name='res.users', string="User")
    operation = fields.Selection(selection=[('receiving', 'Receiving'),
                                            ('qa', 'QA Verification'),
                                            ('finishing', 'Finishing'),
                                            ('login', 'Log In'),
                                            ('logout', 'Log Out')], string='Operation')
    status = fields.Selection(selection=[('success', 'Success'), ('failed', 'Failed')], string='Status')
    date = fields.Datetime(string='Request Datetime', default=fields.Datetime.now)
    requested_data = fields.Text(string="Requested Data")

    @api.model
    def default_get(self, fields_list):
        rec = super().default_get(fields_list)
        if rec.get('request_reference') == '/':
            rec.update({'request_reference': self.env['ir.sequence'].next_by_code('api_request_seq') or '/'})
        return rec
