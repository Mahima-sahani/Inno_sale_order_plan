from odoo import fields, models, api, _
from odoo.exceptions import UserError


class FinishingApiRequest(models.Model):
    _inherit = 'api.request'

    operation = fields.Selection(
        selection_add=[('transfer_data', 'Transfer Data'),('transfer_receive', 'Transfer Receive'),
                       ('transfer_validate', 'Transfer Validate'), ('transfer', 'Transfer')
            ,('request_rcvd', 'Request Received'),('final_rcvd', 'FinishingReceived')],
    )