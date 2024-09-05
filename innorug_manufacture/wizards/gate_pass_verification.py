from odoo import models, fields, api, _
import json


class GatePassVerification(models.TransientModel):
    _name = 'inno.gate.pass.verification'
    _description = 'Will Verify the Gate Pass'

    scan_qr_code = fields.Text(default_focus='1')
    qr_status = fields.Char(compute='onchange_scan_qr_code')

    @api.depends('scan_qr_code')
    def onchange_scan_qr_code(self):
        if self.scan_qr_code:
            if self.scan_qr_code.count('""') > 0:
                qr_data = self.scan_qr_code.split('""')[-1].replace('received_by', '"received_by')
            else:
                qr_data = "{"+self.scan_qr_code+"}"
            qr_data = json.loads(qr_data)
            picking = self.env[qr_data.get('model')].browse(qr_data.get('"id'))
            if picking.is_delivery_out:
                self.write({'scan_qr_code': False, 'qr_status': 'Failed'})
            else:
                # picking.is_delivery_out = True
                self.write({'qr_status': 'Passed'})
                self.scan_qr_code = False
        else:
            self.qr_status = False

