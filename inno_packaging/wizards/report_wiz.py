from odoo import models, fields, api
from odoo.exceptions import UserError, Warning
import logging

_logger = logging.getLogger(__name__)

class ReportWizard(models.TransientModel):

    _name = 'inno.packaging.reports'
    _description = 'Packaging Reports'

    report_type = fields.Selection(selection=[('packagign_current_position','Packaging Current Position'),
                                              ('packing_register','Packing Register'),
                                              ('packing_summary','Packing Summary')])
    unit_area = fields.Selection(selection=[('sq_feet',"Sq Feet"),
                                            ('sq_meter',"Sq Meter"),
                                            ('sq_yard','Sq yard'),
                                            ('sq_cm','Sq CM')], default='sq_feet')
    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')
    subcontractor_id = fields.Many2one('res.partner', string='Subcontractor', tracking=True)
    product_group = fields.Many2many(comodel_name="product.template", string="Product Design")
    product = fields.Many2many(comodel_name="product.product", string="Product")
    division_id = fields.Many2many(comodel_name="mrp.division", string="Division")
    planning_ids = fields.Many2many(comodel_name="sale.order", string="PO No.")
    product_quality = fields.Many2one(comodel_name="inno.invoive.group", string="Invoice Group")
    packing_no = fields.Many2many(comodel_name="inno.packaging", string = "Packing No")
    prod_size = fields.Many2many(comodel_name="product.template.attribute.value", string="Product Size")

    def generate_report(self):
        if self.report_type == 'packagign_current_position':
            
            domain = []

            if self.from_date and self.to_date:
                domain += [('packing_date', '>=', self.from_date), ('packing_date', '<=', self.to_date)]
            elif self.from_date:
                domain += [('packing_date', '=', self.from_date)]
            if self.packing_no:
                ref = self.packing_no.mapped('name')
                domain += [('name', 'in', ref)]

            records = self.env['inno.packaging'].search(domain)
                        
            if self.planning_ids:
                records = records.filtered(lambda rec: any(order.inno_sale_id.id in self.planning_ids.ids for order in rec.stock_quant_lines))
            
            if self.product_quality:
                records = records.stock_quant_lines.filtered(lambda rec: rec.invoice_group_id.id == self.product_quality.id).inno_package_id

            report = self.env.ref('inno_packaging.action_reports_packaging_position',
                                    raise_if_not_found=False).report_action(docids=records.ids,
                                                                            data={
                                                                                'docids': records.ids,
                                                                                'to_date': self.to_date.strftime('%d/%b/%y') if self.to_date else False,
                                                                                'from_date': self.from_date.strftime('%d/%b/%y') if self.from_date else False,
                                                                                })
            return report
        
        if self.report_type == 'packing_register':
            
            domain = []

            if self.product:
                domain += [('product_id','in',self.product.ids)]
            if self.planning_ids:
                domain += [('inno_sale_id','in',self.planning_ids.ids)]
            if self.product_quality:
                domain += [('invoice_group_id','=',self.product_quality.id)]

            records = self.env['stock.quant'].search(domain)

            if self.packing_no:
                ref = self.packing_no.mapped('name')
                records = records.filtered(lambda rec: rec.inno_package_id.name in ref)
            if self.from_date and self.to_date:
                records = records.filtered(lambda rec: rec.inno_package_id.packing_date != False and rec.inno_package_id.packing_date >= self.from_date and rec.inno_package_id.packing_date <= self.to_date)
            elif self.from_date:
                records = records.filtered(lambda rec: rec.inno_package_id.packing_date != False and rec.inno_package_id.packing_date >= self.from_date)
            if self.product_group:
                records = records.filtered(lambda rec: rec.product_id.product_tmpl_id.id in self.product_group.ids)
            if self.prod_size:
                size_name = self.prod_size.mapped('name')
                records = records.filtered(lambda rec: any(varnt.product_template_variant_value_ids.name != False and varnt.product_template_variant_value_ids.name in size_name for varnt in rec.product_id))


            report = self.env.ref('inno_packaging.action_reports_packaging_register',
                                    raise_if_not_found=False).report_action(docids=records.ids,
                                                                            data={
                                                                                'docids': records.ids,
                                                                                'to_date': self.to_date.strftime('%d/%b/%y') if self.to_date else False,
                                                                                'from_date': self.from_date.strftime('%d/%b/%y') if self.from_date else False,
                                                                                })
            return report
        
        if self.report_type == 'packing_summary':
            
            domain = []
            if self.product:
                domain += [('product_id','in',self.product.ids)]
            if self.planning_ids:
                domain += [('inno_sale_id','in',self.planning_ids.ids)]
            if self.product_quality:
                domain += [('invoice_group_id','=',self.product_quality.id)]

            records = self.env['stock.quant'].search(domain)

            if self.packing_no:
                ref = self.packing_no.mapped('name')
                records = records.filtered(lambda rec: rec.inno_package_id.name in ref)
            
            if self.from_date and self.to_date:
                records = records.filtered(lambda rec: rec.inno_package_id.packing_date != False and rec.inno_package_id.packing_date >= self.from_date and rec.inno_package_id.packing_date <= self.to_date)
            elif self.from_date:
                records = records.filtered(lambda rec: rec.inno_package_id.packing_date != False and rec.inno_package_id.packing_date >= self.from_date)
            
            if self.product_group:
                records = records.filtered(lambda rec: rec.product_id.product_tmpl_id.id in self.product_group.ids)

            if self.prod_size:
                size_name = self.prod_size.mapped('name')
                records = records.filtered(lambda rec: any(varnt.product_template_variant_value_ids.name != False and varnt.product_template_variant_value_ids.name in size_name for varnt in rec.product_id))

            report = self.env.ref('inno_packaging.action_reports_packing_summary',
                                    raise_if_not_found=False).report_action(docids=records.ids,
                                                                            data={
                                                                                'docids': records.ids,
                                                                                'unit_area': self.unit_area if self.unit_area else False,
                                                                                'to_date': self.to_date.strftime('%d/%b/%y') if self.to_date else False,
                                                                                'from_date': self.from_date.strftime('%d/%b/%y') if self.from_date else False,
                                                                                })
            return report
