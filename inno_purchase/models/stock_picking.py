from odoo import fields, models, _, api
import logging
import base64
_logger = logging.getLogger(__name__)

class StcckPicking(models.Model):
    _inherit = 'stock.picking'

    inno_purchase_id = fields.Many2one("inno.purchase", string="Purchase No")
    receive_id = fields.Many2one("inno.receive")
    receive_docs = fields.Char("Receive Docs")
    order_type = fields.Selection(related="purchase_id.order_type")
    supplier_date = fields.Datetime(string="Supplier Date")
    receive_by = fields.Many2one("res.partner" ,string="Receive By")

    def button_validate(self):
        res = super(StcckPicking, self).button_validate()
        if self.purchase_id and res:
            report = self.carpet_purchase_challan_report()
            pdf = base64.b64encode(report).decode()
            if report:
                attachment = self.env['ir.attachment'].create({
                    'name': 'Carpet_Purchase_Challan_Report.pdf',
                    'type': 'binary',
                    'datas': pdf,
                    'res_model': self._name,
                    'res_id': self.id,
                })
                self.message_post(
                    body="Purchase order report generated",
                    attachment_ids=[attachment.id]
                )
        else:
            return res
        return res

    def carpet_purchase_challan_report(self):
        report = \
            self.env.ref('inno_purchase.action_carpet_purchase_challan',
                         raise_if_not_found=False).sudo()._render_qweb_pdf(
                'inno_purchase.action_carpet_purchase_challan', res_ids=self.id)[0]
        return report





        



