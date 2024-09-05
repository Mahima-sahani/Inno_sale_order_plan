from odoo import models, fields, api, _
from odoo.exceptions import UserError


class ReportWizard(models.TransientModel):
    _name = 'inno.finishing.reports'
    _description = 'Finishing Reports'

    report_type = fields.Selection(selection=[
        # ('time_incentive', 'Time Incentive'),
                                              ('worker_wise_outstanding_report', 'Worker Wise Outstanding Reports'), ('order_balance', 'Order Balance'),
                                              ('barcode_wise_order_balance', "Barcode Wise Order Balance"), ('finishing_receive_challan', "Finishing Receive Challan"),('receive_reports', 'Receive Register'),
                                              ('payment_advice', 'Payment Advice'),('payment_bill', 'Payment Bill'),('tds_advice', 'TDS Advice'),('material_issue_summary', 'Materials Issue Summary'),
                                              ('barcode_wise_stock_ageing_report', 'Barcode Wise Stock Ageing Report')
        # , ('payment_calculation', 'Payment Calculation'),('payment_calculation', 'Payment Calculation')
                                              # ,('order_summary', 'Order Summary'),('payment_calculation', 'Payment Calculation'),('barcode_stock_ageing', 'Barcode Based Stock Ageing',),
                                              # ('receive_summary', 'Receive Summary'),('finishing_receive_summary', 'Finishing Receive Summary'), ('receive_summary', 'Receive Summary'),
                                              # ('penalty_register', 'Penalty Register'),('freight_summary', 'Freight Summary'),('penalty_register', 'Penalty Register')
    ])
    finishing_order = fields.Many2one(comodel_name='finishing.work.order', string='Order Number')
    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')
    operation_id = fields.Many2one("mrp.workcenter", string="Operations")
    records =  fields.Selection(selection=[('all', 'All'),
                                              ('operations', 'Operations'),],default='all')
    subcontractor_id = fields.Many2one(comodel_name='res.partner', string="Subcontractor")
    finishing_baazar_id = fields.Many2one(comodel_name='finishing.baazar', string="Receive No")


    bazaar_id = fields.Many2one(comodel_name='finishing.baazar', string="Receive No", )
    gst = fields.Selection(selection=[('registered', 'Registered'), ('unregistered', 'Unregistered')],
                           string="GST")
    payment_state = fields.Selection(selection=[
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('reversed', 'Reversed'),
        ('invoicing_legacy', 'Invoicing App Legacy'),
    ], string="Payment Status", )
    with_barcode = fields.Boolean("With Barcode")
    product_design = fields.Many2many(comodel_name="product.template", string="Product Design")
    product_id = fields.Many2many(comodel_name="product.product", string="Product")
    po_number = fields.Many2many(comodel_name="sale.order", string="PO Number")

    stock = fields.Selection(selection=[('inside', 'Inside'), ('outside', 'Outside'), ('all', 'All')], default='all')
    minimum_age = fields.Integer(string="Minimum Age")
    interval = fields.Integer(string="Interval")
    unit = fields.Selection(selection=[('pcs', 'PCS'), ('feet', 'Feet Yard'), ('sq_yard', 'Sq. Yard')], string="Unit")
    prod_custom_group = fields.Char(string="Product Custom Group", default="Custom Order")

    @api.onchange('subcontractor_id', 'operation_id','from_date')
    def get_baazar_domain(self):
        domain = []
        if self.subcontractor_id and self.operation_id and self.from_date:
            domain += [('subcontractor_id', '=', self.subcontractor_id.id),('date', '=', self.from_date)]
            domain = [('id', 'in', self.env['finishing.baazar'].sudo().search(domain).filtered(
                lambda dv: dv.division_id.id in self.env.user.division_id.ids and dv.finishing_work_id.operation_id.id == self.operation_id.id).ids)]
            return {'domain': {'finishing_baazar_id': domain}}
        elif self.subcontractor_id and self.operation_id :
            domain += [('subcontractor_id', '=', self.subcontractor_id.id)]
            domain = [('id', 'in', self.env['finishing.baazar'].sudo().search(domain).filtered(
                lambda
                    dv: dv.division_id.id in self.env.user.division_id.ids and dv.finishing_work_id.operation_id.id == self.operation_id.id).ids)]
            return {'domain': {'finishing_baazar_id': domain}}
        elif self.subcontractor_id and self.from_date :
            domain += [('subcontractor_id', '=', self.subcontractor_id.id),('date', '=', self.from_date)]
            domain = [('id', 'in', self.env['finishing.baazar'].sudo().search(domain).filtered(
                lambda
                    dv: dv.division_id.id in self.env.user.division_id.ids).ids)]
            return {'domain': {'finishing_baazar_id': domain}}
        elif self.subcontractor_id:
            domain += [('subcontractor_id', '=', self.subcontractor_id.id)]
            domain = [('id', 'in', self.env['finishing.baazar'].sudo().search(domain).filtered(
                lambda
                    dv: dv.division_id.id in self.env.user.division_id.ids).ids)]
            return {'domain': {'finishing_baazar_id': domain}}
        elif self.operation_id:
            domain = [('id', 'in', self.env['finishing.baazar'].sudo().search(domain).filtered(
                lambda
                    dv: dv.division_id.id in self.env.user.division_id.ids and dv.finishing_work_id.operation_id.id == self.operation_id.id).ids)]
            return {'domain': {'finishing_baazar_id': domain}}
        else:
            domain = [('id', 'in', self.env['finishing.baazar'].sudo().search(domain).filtered(
                lambda dv: dv.division_id.id in self.env.user.division_id.ids).ids)]
            return {'domain': {'finishing_baazar_id': domain}}

    def generate_report(self):
        if self.report_type == 'barcode_wise_order_balance':
            report = self.env.ref('inno_finishing.action_reports_barcode_wise_order_summary',
                                  ).report_action(docids=self.finishing_order.id, data={'to_date' : self.to_date,'from_date' : self.from_date,'report_type' : self.report_type,'operation_id': self.operation_id.id, 'records' : self.records,
                                  'subcontractor_id': self.subcontractor_id.id if self.subcontractor_id else False })
            return report
        if self.report_type == 'worker_wise_outstanding_report':
            report = self.env.ref('inno_finishing.action_reports_worker_wise_outstanding_report',
                                  ).report_action(docids=self.finishing_order.id,
                                                  data={'to_date': self.to_date, 'from_date': self.from_date,
                                                        'report_type': self.report_type,
                                                        'operation_id': self.operation_id.id, 'records': self.records,
                                                        'subcontractor_id': self.subcontractor_id.id if self.subcontractor_id else False})
            return report
        if self.report_type == 'order_balance':
            domain = [('state','in',['draft','rejected'])]
            process = False

            if self.product_id:
                domain+=[('product_id','in',self.product_id.ids)]

            records = self.env['jobwork.barcode.line'].search(domain)
            
            if self.product_design:
                records = records.filtered(lambda prod: prod.product_id.product_tmpl_id.id in self.product_design.ids)
            if self.po_number:
                records = records.filtered(lambda rec: rec.barcode_id.sale_id.id in self.po_number.ids)

            if self.from_date and self.to_date:
                records = records.filtered(lambda rec: rec.finishing_work_id.issue_date >= self.from_date and rec.finishing_work_id.issue_date <= self.to_date)
            elif self.from_date:
                records = records.filtered(lambda rec: rec.finishing_work_id.issue_date >= self.from_date)
            
            if self.records == "operations":
                if self.operation_id:
                    records = records.filtered(lambda rec: rec.finishing_work_id.operation_id.id == self.operation_id.id)
                    process = self.operation_id.name
                else:
                    process = "All"

            if self.subcontractor_id:
                records = records.filtered(lambda rec: rec.finishing_work_id.subcontractor_id.id == self.subcontractor_id.id)

            report = self.env.ref('inno_finishing.action_report_order_balance_report',
                                  ).report_action(docids=self.finishing_order.id,
                                                  data={
                                                        'docids': records.ids,
                                                        'to_date': self.to_date.strftime('%d/%b/%y') if self.to_date else False, 
                                                        'from_date': self.from_date.strftime('%d/%b/%y') if self.from_date else False,
                                                        'process': process,
                                                        })
            return report
        if self.report_type == 'finishing_receive_challan':
            report = self.env.ref('inno_finishing.action_reports_finishing_finishing_receive_report',
                                  ).report_action(docids=self.finishing_order.id,
                                                  data={'date': self.from_date,
                                                        'vendor': self.subcontractor_id.id,
                                                        'finishing_baazar_id': self.finishing_baazar_id.id,
                                                        'operation_id': self.operation_id.id})
            return report
        if self.report_type in ['payment_bill', ]:
            report = self.env.ref('inno_finishing.action_reports_finishing_payment_bills',
                                  raise_if_not_found=False).report_action(docids=self.bazaar_id.id,
                                                                          data={'to_date': self.to_date,
                                                                                'from_date': self.from_date,
                                                                                'report_type': self.report_type,
                                                                                'order_no': self.finishing_order.id,
                                                                                'receive_no': self.bazaar_id.id,
                                                                                'gst': self.gst,
                                                                                'payment_state': self.payment_state,
                                                                                'operation': self.operation_id.id,
                                                                                'subcontractor_id': self.subcontractor_id.id})
            return report
        if self.report_type in ['payment_advice', ]:
            report = self.env.ref('inno_finishing.action_reports_finsihing_payment_advice',
                                  raise_if_not_found=False).report_action(docids=self.bazaar_id.id,
                                                                          data={'to_date': self.to_date,
                                                                                'from_date': self.from_date,
                                                                                'report_type': self.report_type,
                                                                                'order_no': self.finishing_order.id,
                                                                                'receive_no': self.bazaar_id.id,
                                                                                'gst': self.gst,
                                                                                'payment_state': self.payment_state,
                                                                                'operation': self.operation_id.id,
                                                                                'subcontractor_id': self.subcontractor_id.id})
            return report
        if self.report_type in ['receive_reports', ]:
            report = self.env.ref('inno_finishing.action_reports_finsihing_baazar_reports',
                                  raise_if_not_found=False).report_action(docids=self.bazaar_id.id,
                                                                          data={'to_date': self.to_date.strftime(
                                                                              '%d/%b/%Y') if self.to_date else False,
                                                                                'from_date': self.from_date.strftime(
                                                                                    '%d/%b/%Y') if self.from_date else False,
                                                                                'report_type': self.report_type,
                                                                                'operation' : self.operation_id.id,
                                                                                'with_barcode': self.with_barcode,
                                                                                'subcontractor_id': self.subcontractor_id.id})
            return report
        if self.report_type == 'tds_advice':
            report = self.env.ref('inno_finishing.action_reports_finishing_tds_payment_advice',
                                  raise_if_not_found=False).report_action(docids=self.bazaar_id.id,
                                                                          data={'to_date': self.to_date,
                                                                                'from_date': self.from_date,
                                                                                'operation_id': self.operation_id.id,
                                                                                'records' : self.records,
                                                                                'subcontractor_id': self.subcontractor_id.id if self.subcontractor_id else False, })
            return report
        if self.report_type == 'material_issue_summary':
            report = self.env.ref('inno_finishing.action_reports_materials_issue_summary',
                                  raise_if_not_found=False).report_action(docids=self.bazaar_id.id,
                                                                          data={'to_date': self.to_date,
                                                                                'from_date': self.from_date,
                                                                                'operation_id': self.operation_id.id,
                                                                                'records' : self.records,
                                                                                'subcontractor_id': self.subcontractor_id.id if self.subcontractor_id else False, })
            return report

        if self.report_type == 'barcode_wise_stock_ageing_report':
            domain = []
            records = self.env['mrp.barcode'].search(domain)
            report = self.env.ref('inno_finishing.action_reports_barcode_stock_ageing',
                                  raise_if_not_found=False).report_action(docids=records.ids,
                                                                          data={'docids' : records.ids})
            return report
