from odoo import models, fields, api
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)

class ReportWizard(models.TransientModel):

    _name = 'inno.purchase.reports'
    _description = 'Purchase Reports'

    report_type = fields.Selection(selection=[('purchase_order_balance','Purchase Order Balance report')])
    vendor_id = fields.Many2one(comodel_name="res.partner",string="Vendor")
    purchase_order_no = fields.Many2many(comodel_name="purchase.order", string="Purchase Order No")
    product_id = fields.Many2many(comodel_name="product.product", string="Product")
    to_date =  fields.Date(string="To Date")
    from_date =  fields.Date(string="From Date")

    # division_id = fields.Many2many(comodel_name="mrp.division", string="Division")
    # buyer_id = fields.Many2one(comodel_name="res.partner", string="Buyer", domain=get_buyer_domain)
    # order_type = fields.Selection(selection=[('sale', 'Sale Order'), ('custom', 'Custom Order'),('hospitality', 'Hospitality Custom'), ('local', 'Local')], string="Order Type")
    # product_group = fields.Many2many(comodel_name="product.template", string="Product Group")
    # planning_ids = fields.Many2many(comodel_name="inno.sale.order.planning", string="PO No.")

    def generate_report(self):
        report = False

        if self.report_type == 'purchase_order_balance':
            domain = []

            if self.vendor_id:
                domain+=[('partner_id','=',self.vendor_id.id)]
            if self.purchase_order_no:
                domain+=[('id','in',self.purchase_order_no.ids)]
            if self.from_date and self.to_date:
                domain += [('date_approve', '>=', self.from_date), ('date_approve', '<=', self.to_date)]
            elif self.from_date:
                domain.append(('date_approve', '=', self.from_date))

            records = self.env['purchase.order'].search(domain)
            
            if self.product_id:
                records = records.filtered(lambda rec: any(line.product_id.id in self.product_id.ids for line in rec.order_line))
            
            report = self.env.ref('inno_purchase.action_reports_purchase_order_balance',
                                raise_if_not_found=False).report_action(docids=records.ids,
                                                                        data={
                                                                            'to_date': self.to_date.strftime('%d/%b/%Y') if self.to_date else False,
                                                                            'from_date': self.from_date.strftime('%d/%b/%Y') if self.from_date else False,
                                                                            'docids': records.ids,
                                                                            'vendor': self.vendor_id.name if self.vendor_id else False,
                                                                            })
        return report
