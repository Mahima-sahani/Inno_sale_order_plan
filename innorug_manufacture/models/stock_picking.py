from odoo import fields, models, api, _
import base64

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    main_jobwork_id = fields.Many2one(comodel_name='main.jobwork')
    is_delivery_out = fields.Boolean()
    division_id = fields.Many2one(comodel_name='mrp.division', related='main_jobwork_id.division_id')
    doc_date = fields.Date(string='Doc Date')

    def button_validate(self):
        for rec in self:
            res = super().button_validate()
            if rec.main_jobwork_id and res == True:
                for material in rec.move_ids:
                    rec.sudo().main_jobwork_id.main_jobwork_components_lines.filtered(
                        lambda mat: mat.product_id.id == material.product_id.id).quantity_released += material.quantity_done
            if res == True and rec.picking_type_id.code in ['outgoing', 'internal']:
                pdf = self.env.ref('innorug_manufacture.action_report_material_gate_pass',
                                   raise_if_not_found=False).sudo()._render_qweb_pdf(
                    'innorug_manufacture.action_report_material_gate_pass', res_ids=rec.id,
                    data={'type': rec.picking_type_id.code})[0]
                pdf = base64.b64encode(pdf).decode()
                attachment = self.env['ir.attachment'].create({'name': f"Gate Pass: {self.name}",
                                                               'type': 'binary',
                                                               'datas': pdf,
                                                               'res_model': 'stock.picking',
                                                               'res_id': rec.id,
                                                               })
                rec.message_post(body="Gate Pass Generated", attachment_ids=[attachment.id])
            return res


class StockMove(models.Model):
    _inherit = 'stock.move'

    changeable_cloth = fields.Boolean(related='product_id.changeable_cloth')
    remarks = fields.Text("Remarks")

    def add_different_clothes(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Update Cloth"),
            'view_mode': 'form',
            'res_model': 'inno.update.cloth',
            'context':  {'default_move_id': self.id, 'default_picking_id': self.picking_id.id},
            'target': 'new'
        }
