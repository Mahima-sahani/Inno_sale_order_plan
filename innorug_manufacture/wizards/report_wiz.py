from odoo import models, fields, api, _
from odoo.exceptions import UserError
import logging

_logger = logging.getLogger(__name__)


class ReportWizard(models.TransientModel):
    _name = 'inno.weaving.reports'
    _description = 'Weaving Reports'

    def get_buyer_domain(self):
        domain = [
            ('id', 'in',
             self.env['sale.order'].search([('state', '!=', 'done'), ('state', '!=', 'cancel')]).partner_id.ids)]
        return domain

    report_type = fields.Selection(selection=[('weaving_order_status', 'Weaving Order Status'),
                                              ('to_be_issue', 'To Be Issue'), ('purja', 'Hisab of Purja'),
                                              ('per_day_weaving_report', "Today's Weaving Report"),
                                              ('jw_weaving_ledger', 'JobWorker Wise Weaving Ledger'), (
                                                  'weaving_order_barcode_balance_for_inspection',
                                                  'Weaving Order Barcode Balance For Inspection'),
                                              ('weaving_order_product_balance_for_inspection',
                                               'Weaving Order Product Balance For Inspection'),
                                              ("baazar_repots", "Baazar Register"),
                                              ("weaving_bazar_receipt", "Weaving Bazar Receipt"),
                                              ("weaving_material_issue", "Weaving Material Issue"),
                                              ("weaving_material_receive", "Weaving Material Receive"),
                                              ("weaving_payment_advice", "Weaving Payment Advice"),("weaving_bills", "Weaving Bills"),("cheque_details", "Cheque Details"),("tds_advice", "TDS Advice"),
                                              ("weaving_order","Weaving Order"),
                                              ("material_on_loom", "Material On Loom")])
    weaving_order = fields.Many2one(comodel_name='main.jobwork', string='Document Number')
    include_branch = fields.Boolean(string='Include Branch Records')
    from_date = fields.Date(string='From Date')
    to_date = fields.Date(string='To Date')
    subcontractor_id = fields.Many2one('res.partner', string='Subcontractor', tracking=True)
    job_work_id = fields.Many2one(comodel_name="main.jobwork", string="Order No", )
    bazaar_id = fields.Many2one(comodel_name='main.baazar', string="Receive No", )
    buyer = fields.Many2one(comodel_name="res.partner", string="Buyer", domain=get_buyer_domain)
    product_group = fields.Many2many(comodel_name="product.template", string="Product Group")
    product = fields.Many2many(comodel_name="product.product", string="Product")
    order_type = fields.Selection(selection=[('sale', 'Sale Order'), ('custom', 'Custom Order'),
                                             ('hospitality', 'Hospitality Custom'), ('local', 'Local')],
                                  string="Order Type")
    gst = fields.Selection(selection=[('registered', 'Registered'), ('unregistered', 'Unregistered')],
                           string="GST")
    division_id = fields.Many2many(comodel_name="mrp.division", string="Division")
    weaving_summary = fields.Boolean(string="Weaving Summary")
    planning_ids = fields.Many2many(comodel_name="sale.order", string="PO No.")
    cheque_no = fields.Char(string="Cheque No")
    payment_date = fields.Date(string="Payment Date")
    report_wise = fields.Selection(selection=[('month_wise','Month Wise Report'),('issue_wise','Issue No Wise Report')])
    weavng_wise_report = fields.Selection(selection=[('design_wise','Design Wise Report')])

    payment_state = fields.Selection(selection=[
        ('not_paid', 'Not Paid'),
        ('in_payment', 'In Payment'),
        ('paid', 'Paid'),
        ('partial', 'Partially Paid'),
        ('reversed', 'Reversed'),
        ('invoicing_legacy', 'Invoicing App Legacy'),
    ], string="Payment Status", )
    exclude_branch = fields.Boolean(string='Exclude Branch Records')
    branch_id = fields.Many2one("weaving.branch", string="Branch")
    is_branch_vendor = fields.Boolean(string='Branch Vendor')
    with_barcode = fields.Boolean("With Barcode")

    @api.onchange('report_type', )
    def get_main_job_work_domain(self):
        domain = [('id', 'in', self.env['main.jobwork'].sudo().search([]).ids)]
        return {'domain': {'weaving_order': domain}}

    @api.onchange('job_work_id', 'subcontractor_id')
    def get_baazar_domain(self):
        domain = []
        if self.job_work_id:
            domain += [('main_jobwork_id', '=', self.job_work_id.id)]
        elif self.subcontractor_id:
            domain += [('subcontractor_id', '=', self.subcontractor_id.id)]
        domain = [('id', 'in', self.env['main.baazar'].sudo().search(domain).filtered(
            lambda dv: dv.division_id.id in self.env.user.division_id.ids).ids)]
        return {'domain': {'bazaar_id': domain}}

    @api.onchange('subcontractor_id')
    def get_job_work_domain(self):
        domain = []
        if self.subcontractor_id:
            domain += [('subcontractor_id', '=', self.subcontractor_id.id)]
        domain = [('id', 'in', self.env['main.jobwork'].sudo().search(domain).filtered(
            lambda dv: dv.division_id.id in self.env.user.division_id.ids).ids)]
        return {'domain': {'job_work_id': domain}}

    @api.onchange('from_date', 'to_date', 'subcontractor_id')
    def onchange_user_id(self):
        if self.from_date and self.report_type in ['weaving_order_barcode_balance_for_inspection',
                                                   'weaving_order_product_balance_for_inspection']:
            self.subcontractor_id = False
        if self.subcontractor_id and self.report_type in ['weaving_order_barcode_balance_for_inspection',
                                                          'weaving_order_product_balance_for_inspection']:
            self.from_date = False
            self.to_date = False

    def generate_report(self):
        report = False
        if self.report_type == 'purja':
            report = self.env.ref('innorug_manufacture.action_report_cost_center_id',
                                  raise_if_not_found=False).report_action(docids=self.weaving_order.id)
        if self.report_type == 'weaving_order_status':
            domain = []
            if self.include_branch and self.env['ir.module.module'].search(
                    [('name', '=', 'inno_weaving_branch')]).state == 'installed':
                domain.append(('parent_job_work_id', '=', False))
            if self.env['ir.module.module'].search([('name', '=', 'inno_weaving_branch')]).state != 'installed':
                raise UserError(_("Branch is not Active"))
            else:
                domain.extend([('parent_job_work_id', '=', False), ('branch_id', '=', False)])

            if self.from_date and self.to_date:
                domain += [('issue_date', '>=', self.from_date), ('issue_date', '<=', self.to_date)]
            elif self.from_date:
                domain += [('issue_date', '>=', self.from_date)]
            if self.subcontractor_id:
                domain += [('subcontractor_id', '=', self.subcontractor_id.id)]

            weaving_orders = self.env['main.jobwork'].sudo().search(domain)

            if self.product:
                weaving_orders = weaving_orders.filtered(
                    lambda rec: any(line.product_id.id in self.product.ids for line in rec.jobwork_line_ids))

            if self.product_group:
                weaving_orders = weaving_orders.filtered(lambda rec: any(
                    line.product_id.product_tmpl_id.id in self.product_group.ids for line in rec.jobwork_line_ids))

            if self.planning_ids:
                weaving_orders = weaving_orders.filtered(lambda rec: rec.sale_id.id in self.planning_ids.ids)

            report = self.env.ref('innorug_manufacture.action_weaving_order_status_summary',
                                  raise_if_not_found=False).report_action(docids=weaving_orders.ids,
                                                                          data={'start_date': self.from_date,
                                                                                'end_date': self.to_date,
                                                                                'include_branch': self.include_branch})
        if self.report_type == 'to_be_issue':

            domain = [('workcenter_id.is_weaving_workcenter', '=', True), ('allotment', '!=', 'full'),
                      ('division_id', 'in', self.env.user.division_id.ids)]

            if self.buyer:
                domain += [('sale_id.partner_id', '=', int(self.buyer.id))]
            if self.product_group:
                domain += [('product_tmpl_id', 'in', self.product_group.ids)]
            if self.product:
                domain += [('product_id', 'in', self.product.ids)]
            if self.division_id:
                domain += [('division_id', 'in', self.division_id.ids)]
            if self.planning_ids:
                domain += [('sale_id', 'in', self.planning_ids.ids)]
            if self.from_date and self.to_date:
                domain += [('sale_order_date', '>=', self.from_date), ('sale_order_date', '<=', self.to_date)]
            elif self.from_date:
                domain.append(('sale_order_date', '=', self.from_date))

            work_orders = self.env['mrp.workorder'].sudo().search(domain)
            if self.order_type:
                order_type = self.env['inno.sale.order.planning'].search(
                    [('order_type', '=', self.order_type), ('sale_order_id', 'in', work_orders.sale_id.ids)])
                work_orders = work_orders.filtered(lambda wo: wo.sale_id.id in order_type.sale_order_id.ids)

            if not work_orders:
                raise UserError(_("Job work not found"))

            report = self.env.ref('innorug_manufacture.action_weaving_to_be_issue',
                                  raise_if_not_found=False).report_action(docids=work_orders.ids)
        if self.report_type in ['weaving_order_barcode_balance_for_inspection',
                                'weaving_order_product_balance_for_inspection']:

            po_number = False
            if self.planning_ids:
                po_number = ""
                for po in self.planning_ids:
                    po_number += po.order_no + " , "
            report = self.env.ref('innorug_manufacture.action_reports_weaving_order_barcode_balance_for_inspection',
                                  raise_if_not_found=False).report_action(docids=self.weaving_order.id,
                                                                          data={'to_date': self.to_date,
                                                                                'from_date': self.from_date,
                                                                                'report_type': self.report_type,
                                                                                'order_type': self.order_type,
                                                                                'subcontractor_id': self.subcontractor_id.id,
                                                                                'buyer': self.buyer.id if self.buyer.id else False,
                                                                                'product_group': self.product_group.ids if self.product_group.ids else False,
                                                                                'product': self.product.ids if self.product.ids else False,
                                                                                'order_type': self.order_type if self.order_type else False,
                                                                                'division_id': self.division_id.ids if self.division_id else False,
                                                                                'planing_ids': self.planning_ids.ids if self.planning_ids else False,
                                                                                'po_number': po_number if po_number else False})
        if self.report_type == 'baazar_repots':
            report = self.env.ref('innorug_manufacture.action_report_print_bazaar_size_wise_receiving',
                                  raise_if_not_found=False).report_action(docids=self.weaving_order.id,
                                                                          data={'to_date': self.to_date,
                                                                                'from_date': self.from_date,
                                                                                'report_type': self.report_type,
                                                                                'buyer_id': self.buyer.id,
                                                                                'po_no': self.planning_ids.ids,
                                                                                'product_id': self.product.ids,
                                                                                'product_group': self.product_group.ids,
                                                                                'subcontractor_id': self.subcontractor_id.id,
                                                                                'include_branch': self.include_branch,
                                                                                'exclude_branch': self.exclude_branch,
                                                                                'branch_id': self.branch_id.id,
                                                                                'is_branch_vendor': self.is_branch_vendor,
                                                                                'with_barcode': self.with_barcode})
        if self.report_type == 'weaving_bazar_receipt':
            domain = [('division_id', 'in', self.env.user.division_id.ids)]
            if self.subcontractor_id:
                domain += [('subcontractor_id', '=', self.subcontractor_id.id)]
            if self.from_date and self.to_date:
                domain += [('date', '>=', self.from_date), ('date', '<=', self.to_date)]
            elif self.from_date:
                domain.append(('date', '=', self.from_date))

            records = self.env['main.baazar'].search(domain)
            report = self.env.ref('innorug_manufacture.action_weaving_bazar_receipt',
                                  raise_if_not_found=False).report_action(docids=records.ids,
                                                                          data={'from_date': self.from_date.strftime(
                                                                              '%d/%b/%Y') if self.from_date else False,
                                                                                'subcontractor_id': self.subcontractor_id.id,
                                                                                'docids': records.ids})
        if self.report_type in ['weaving_bills', ]:
            report = self.env.ref('innorug_manufacture.action_reports_weaving_payment_bills',
                                  raise_if_not_found=False).report_action(docids=self.weaving_order.id,
                                                                          data={'to_date': self.to_date,
                                                                                'from_date': self.from_date,
                                                                                'report_type': self.report_type,
                                                                                'order_no': self.job_work_id.id,
                                                                                'receive_no': self.bazaar_id.id,
                                                                                'gst': self.gst,
                                                                                'payment_state': self.payment_state,
                                                                                'subcontractor_id': self.subcontractor_id.id,
                                                                                'include_branch': self.include_branch,
                                                                                'exclude_branch': self.exclude_branch,
                                                                                'branch_id': self.branch_id.id,
                                                                                'is_branch_vendor': self.is_branch_vendor})
        if self.report_type in ['weaving_payment_advice', ]:
            report = self.env.ref('innorug_manufacture.action_reports_weaving_payment_advice',
                                  raise_if_not_found=False).report_action(docids=self.weaving_order.id,
                                                                          data={'to_date': self.to_date,
                                                                                'from_date': self.from_date,
                                                                                'report_type': self.report_type,
                                                                                'order_no': self.job_work_id.id,
                                                                                'receive_no': self.bazaar_id.id,
                                                                                'gst': self.gst,
                                                                                'payment_state': self.payment_state,
                                                                                'subcontractor_id': self.subcontractor_id.id,
                                                                                'include_branch': self.include_branch,
                                                                                'exclude_branch': self.exclude_branch,
                                                                                'branch_id': self.branch_id.id,
                                                                                'is_branch_vendor': self.is_branch_vendor})

        if self.report_type in ['weaving_material_issue', 'weaving_material_receive']:

            domain = [('division_id', 'in', self.env.user.division_id.ids)]
            # Add conditions based on provided parameters
            if self.subcontractor_id:
                domain.append(('partner_id', '=', self.subcontractor_id.id))
            if self.from_date and self.to_date:
                domain += [('date_done', '>=', self.from_date), ('date_done', '<=', self.to_date)]
            elif self.from_date:
                domain.append(('date_done', '=', self.from_date))
            # Search for stock pickings based on the domain
            records = self.env['stock.picking'].search(domain)

            if self.weaving_summary == True:
                if self.report_wise == 'month_wise':
                    report = self.env.ref('innorug_manufacture.action_weaving_material_issue_summary_date_wise',
                                          raise_if_not_found=False).report_action(
                        docids=records.ids,
                        data={
                            'to_date': self.to_date.strftime('%d/%b/%Y') if self.to_date else False,
                            'from_date': self.from_date.strftime('%d/%b/%Y') if self.from_date else False,
                            'report_type': self.report_type,
                            'subcontractor_id': self.subcontractor_id.name if self.subcontractor_id else False,
                            'docids': records.ids
                        }
                    )
                elif self.report_wise == "issue_wise":
                    report = self.env.ref('innorug_manufacture.action_weaving_material_issue_wise_summary',
                                          raise_if_not_found=False).report_action(
                        docids=records.ids,
                        data={
                            'to_date': self.to_date.strftime('%d/%b/%Y') if self.to_date else False,
                            'from_date': self.from_date.strftime('%d/%b/%Y') if self.from_date else False,
                            'report_type': self.report_type,
                            'subcontractor_id': self.subcontractor_id.name if self.subcontractor_id else False,
                            'docids': records.ids
                        }
                    )

                else:
                    report = self.env.ref('innorug_manufacture.action_weaving_material_issue_summary',
                                          raise_if_not_found=False).report_action(
                        docids=records.ids,
                        data={
                            'to_date': self.to_date.strftime('%d/%b/%Y') if self.to_date else False,
                            'from_date': self.from_date.strftime('%d/%b/%Y') if self.from_date else False,
                            'report_type': self.report_type,
                            'subcontractor_id': self.subcontractor_id.name if self.subcontractor_id else False,
                            'docids': records.ids
                        }
                    )
            else:
                report = self.env.ref('innorug_manufacture.action_weaving_material_issue',
                                      raise_if_not_found=False).report_action(
                    docids=records.ids,
                    data={
                        'to_date': self.to_date.strftime('%d/%b/%Y') if self.to_date else False,
                        'from_date': self.from_date.strftime('%d/%b/%Y') if self.from_date else False,
                        'report_type': self.report_type,
                        'subcontractor_id': self.subcontractor_id.name if self.subcontractor_id else False,
                        'docids': records.ids
                    }
                )
        if self.report_type == 'tds_advice':
            report = self.env.ref('innorug_manufacture.action_reports_tds_payment_advice',
                                  raise_if_not_found=False).report_action(docids=self.weaving_order.id,
                                                                          data={'to_date': self.to_date,
                                                                                'from_date': self.from_date,
                                                                                'subcontractor_id': self.subcontractor_id.name if self.subcontractor_id else False,
                                                                                'include_branch': self.include_branch,
                                                                                'exclude_branch': self.exclude_branch,
                                                                                'branch_id': self.branch_id.id,
                                                                                'is_branch_vendor': self.is_branch_vendor
                                                                                })

        if self.report_type == 'cheque_details':

            domain = []
            if self.cheque_no:
                domain += [('cheque', '=', self.cheque_no)]
            elif self.payment_date:
                domain.append(('date', '=', self.payment_date))

            records = self.env['account.payment'].search(domain)
            report = self.env.ref('innorug_manufacture.action_reports_weaving_cheque_details',
                                raise_if_not_found=False).report_action(docids=records.ids,
                                                                        data={'payment_date': self.payment_date.strftime(
                                                                            '%d/%b/%Y') if self.payment_date else False,
                                                                                'cheque_no': self.cheque_no,
                                                                                'docids': records.ids})
            
        if self.report_type == "weaving_order":
            domain = []

            product_name = [pro_name.default_code for pro_name in self.product if self.product]
            pro_name = ",".join(product_name)

            division_name = [div.name for div in self.division_id if self.division_id]
            div_name = ",".join(division_name)

            if self.subcontractor_id:
                domain += [('subcontractor_id', '=', self.subcontractor_id.id)]
            if self.from_date and self.to_date:
                domain += [('issue_date', '>=', self.from_date), ('issue_date', '<=', self.to_date)]
            elif self.from_date:
                domain += [('issue_date', '=', self.from_date)]
            if self.buyer:
                domain += [('subcontractor_id','=',self.subcontractor_id.id)]
            if self.division_id:
                domain += [('division_id','in',self.division_id.ids)]
            
            records = self.env['mrp.job.work'].search(domain)
            
            if self.product:
                records = records.filtered(lambda rec: rec.product_id.id in self.product.ids)
            
            if self.product_group:
                records = records.filtered(lambda rec: rec.product_id.product_tmpl_id.id in self.product_group.ids)
            
            if self.planning_ids:
                records = records.filtered(lambda rec: rec.mrp_work_order_id.sale_id.id in self.planning_ids.ids)

            report = self.env.ref('innorug_manufacture.action_report_weaving_order', raise_if_not_found=False).report_action(docids=records.ids,
                                                                        data={
                                                                            'docids': records.ids,
                                                                            'to_date': self.to_date,
                                                                            'from_date': self.from_date,
                                                                            'weavng_wise_report': self.weavng_wise_report if self.weavng_wise_report else False,
                                                                            'division': div_name if div_name else False,
                                                                            'product': pro_name if pro_name else False
                                                                            })
        if self.report_type == "material_on_loom":
            domain = []

            if self.from_date and self.to_date:
                domain += [('issue_date', '>=', self.from_date), ('issue_date', '<=', self.to_date)]
            elif self.from_date:
                domain += [('issue_date', '>=', self.from_date)]
            if self.subcontractor_id:
                domain += [('subcontractor_id', '=', self.subcontractor_id.id)]

            records = self.env['main.jobwork'].search(domain)
            report = self.env.ref('innorug_manufacture.action_report_material_loom', raise_if_not_found=False).report_action(docids=records.ids,
                                                                        data={
                                                                            'docids': records.ids,
                                                                            'to_date': self.to_date.strftime('%d/%b/%y') if self.to_date else False,
                                                                            'from_date': self.from_date.strftime('%d/%b/%y') if self.from_date else False,
                                                                            'subcontractor':self.subcontractor_id.name
                                                                            })


        return report
