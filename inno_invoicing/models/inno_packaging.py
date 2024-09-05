from odoo import models, fields, api
from odoo.exceptions import UserError, ValidationError, MissingError
from datetime import datetime


class InvoicingW(models.Model):
    _inherit = 'inno.packaging'

    invoice_name = fields.Char(string='Reference', default='/')
    invoice = fields.Date("Invoice Date")
    currency_id = fields.Many2one('res.currency',"Currency")
    exchange_rate = fields.Float("Exchange Rate")
    delivery_terms = fields.Selection([('fob', 'F.O.D'),('cif', 'C.I.F'),('free_trade_samples', 'Free Trade Samples'),('candf', 'C & F')], string="Delivery Terms")
    blno = fields.Char("B.L.No")
    bl_date = fields.Date("B.L. Date")
    private_mark = fields.Char("Private Mark")
    port_of_loading = fields.Char("Port of Loading")
    desination_port = fields.Char("Destination Port")
    final_plc_dlvery = fields.Char("Final Place of Delivery")
    circular_no = fields.Char("Circular No")
    circular_date = fields.Date("Circular Date")
    order_no = fields.Char("Order No")
    order_date = fields.Date("Order Date")
    kinds_of_pkg = fields.Float("Kinds of Package")
    invoice_amt = fields.Float("Invoice Amount")
    freight = fields.Char("Freight")
    insurance = fields.Char("Insurance")
    vehicle_no = fields.Char("Vehicle No")
    other_ref = fields.Char("Other Reference")
    terms_of_sale= fields.Text("Terms of Sale")
    notify_party = fields.Char("Notify Party")
    pkg_material_desc = fields.Char("Packing Material Description")
    desc_of_goods = fields.Text("Description of Goods")
    compositions = fields.Text("Composition")
    remark = fields.Text("Remark")

    def generate_reports(self):
        data = {}
        report = self.env.ref('inno_invoicing.action_report_print_order_invoice_xlsx').report_action(self, data=data)
        return report

    def button_action_for_packaging_done(self):
        rec = super().button_action_for_packaging_done()
        if self.invoice_name == '/':
            self.update({'invoice_name': self.env['ir.sequence'].next_by_code('inno_invoicing_seq') or '/'})
            no = 0
            for line in self.stock_quant_lines:
                no += 1
                line.write({'sequence_ref' : no, 'rate':self.env['inno.sale.order.planning'].search([('sale_order_id', 'in',line.sale_order_id.ids)]).sale_order_planning_lines.filtered(lambda pl: line.product_id.id in pl.product_id.ids).rate * line.quantity })
            if not self.currency_id:
                self.write({'currency_id' :self.stock_quant_lines.sale_order_id.currency_id.id, })
        return rec

    def button_action_for_create_invoice(self):
        self.status = 'done'

    def button_action_for_generate_report(self):
        return {
            'type': 'ir.actions.act_window',
            'name': "Reports",
            'view_mode': 'form',
            'res_model': 'invoice.report.wizard',
            'target': 'new'
        }
