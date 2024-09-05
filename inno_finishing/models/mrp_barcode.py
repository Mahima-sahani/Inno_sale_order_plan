from odoo import models, fields, _
from odoo.exceptions import UserError, ValidationError, MissingError


class Barcode(models.Model):
    _inherit = 'mrp.barcode'

    finishing_jobwork_id = fields.Many2one(comodel_name='finishing.work.order', tracking=True)
    full_finishing = fields.Boolean(string="Full Finishing",  tracking=True)
    transfer_id = fields.Many2one(comodel_name="inno.carpet.transfer", string="Transfer",  tracking=True)



    def button_action_skip_process(self):
        if self.transfer_id:
            raise UserError(_("This barcode is transfer mode"))
        parent_id = self.env['mrp.workorder'].sudo().search(
            [('parent_id', '=', self.next_process.id)])
        if parent_id and self.next_process.id:
            wizard_size_id = self.env['finishing.operation.wizard'].create({
                'barcode_id': self.id,
                'next_operation': parent_id.id,
            })
            return {
                'type': 'ir.actions.act_window',
                'name': ("Skip Process"),
                'view_mode': 'form',
                'view_id': self.env.ref('inno_finishing.view_inno_finishing_skip_reason_wizard').id,
                'res_model': 'finishing.operation.wizard',
                'res_id': wizard_size_id.id,
                "target": "new",
            }
        else:
            raise UserError(_("You cannot skip this operation, this operation is mandatory"))

    def button_action_undo_skip(self, barcode_id):
        if self.transfer_id:
            raise UserError(_("This barcode is transfer mode"))
        barcode = self.browse(barcode_id)
        parent_id = barcode.next_process.parent_id
        if parent_id and barcode:
            barcode.write({'next_process': parent_id.id})
            parent_id.finished_qty -= 1
            barcode.message_post(body=f'Skip Process Undo (User By mistake skipped the process)')
        else:
            raise UserError(_("You cannot skip this operation, this operation is mandatory"))
