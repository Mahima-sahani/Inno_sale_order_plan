import base64
from odoo import fields, models, _, api
from odoo.exceptions import UserError
from datetime import timedelta
from dateutil import relativedelta
from datetime import datetime

class InnoReceiveProducts(models.TransientModel):
    _name = "inno.receive.wizard"
    _description = 'Receive Wizards'

    subcontractor_id = fields.Many2one('res.partner', string='Vendor', tracking=True)
    receive_docs = fields.Char("Vendor Receive No")
    date = fields.Date(string='Date Issued', default=lambda *a: datetime.now(), )
    location = fields.Many2one("stock.location", string="Destination Location",default=lambda self: self.env.user.material_location_id.id)
    inno_purchase_id = fields.Many2one("inno.purchase", string="Purchase No")
    supplier_date = fields.Date(string='Supplier Challan Date', )

    @api.model
    def default_get(self, fields_list):
        rec = super().default_get(fields_list)
        po = self.env['inno.purchase'].browse(self._context.get('active_id'))
        config_id = self.env["inno.config"].sudo().search([], limit=1)
        if po:
            rec.update({'inno_purchase_id': po.id, 'subcontractor_id': po.subcontractor_id.id,})
        return rec

    def do_confirm(self):
        docs=self.inno_purchase_id.inno_receive_ids.filtered(lambda rd: rd.receive_docs == self.receive_docs)
        if docs:
            raise UserError(_("Already Received"))
        if not docs:
            line=[(0,0,{'product_id': rec.product_id.id,'label': rec.product_id.name, 'discount': rec.discount, 'tax_id':[(4, tx.id) for tx in rec.tax_id] ,'uom_id': rec.product_id.uom_id.id,'purchase_line_id': rec.id,
                        'demand_qty': rec.product_qty - rec.receive_qty if rec.inno_purchase_id.types == 'purchase' else rec.product_qty - rec.invoice_qty, 'demand_deal_qty' : rec.deal_qty - rec.invoice_qty if rec.inno_purchase_id.types == 'purchase' else 0,
                        'deal_uom_id': rec.deal_uom_id.id if rec.inno_purchase_id.types == 'purchase' else False ,'rate': rec.rate}) for rec in self.inno_purchase_id.inno_purchase_line]
            self.inno_purchase_id.write({'inno_receive_ids': [(0, 0, {'subcontractor_id': self.subcontractor_id.id, 'types': self.inno_purchase_id.types, 'receive_docs': self.receive_docs,'supplier_date': self.supplier_date,
                                                 'date': self.date,'location': self.location.id,'inno_purchase_id': self.inno_purchase_id.id, })]})
            docs = self.inno_purchase_id.inno_receive_ids.filtered(lambda rd: rd.receive_docs == self.receive_docs)
            docs.create_sequence()
            docs.write({'inno_receive_line': [(0,0,{'label': "Frieght Charge", 'invoice_qty': 1,'uom_id':  self.env['uom.uom'].search([('name', '=', 'Units')], limit=1).id}),(0,0,{'label': "Other", 'invoice_qty': 1,'uom_id':  self.env['uom.uom'].search([('name', '=', 'Units')], limit=1).id})]})
            docs.write({'inno_receive_line': line,})

            return {
                'type': 'ir.actions.act_window',
                'name': "Receive Products",
                'view_mode': 'form',
                'res_model': 'inno.receive',
                'res_id': docs.id
            }
class Return_Picking(models.TransientModel):
    _inherit = 'stock.return.picking'