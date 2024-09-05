from odoo import fields, models, _, api
import base64
import logging

_logger = logging.getLogger(__name__)

class AccountMove(models.Model):
    _inherit = 'account.move'

    receive_invoice = fields.Char("Vendor Invoice No")
    inno_purchase_id = fields.Many2one("inno.purchase", string="Purchase No")
    receive_id = fields.Many2one("inno.receive")
    supplier_date = fields.Date(string="Supplier Date")

    order_type = fields.Selection(related="purchase_id.order_type")

    def action_post(self):

        res = super(AccountMove, self).action_post()
        
        line = self.invoice_line_ids.purchase_line_id
        if line:
            report = self.carpet_purchase_invoice_report()
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

    def carpet_purchase_invoice_report(self):
        report = \
            self.env.ref('inno_purchase.action_carpet_purchase_invoice',
                         raise_if_not_found=False).sudo()._render_qweb_pdf(
                'inno_purchase.action_carpet_purchase_invoice', res_ids=self.id)[0]
        return report


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    remarks = fields.Text("Remarks")
