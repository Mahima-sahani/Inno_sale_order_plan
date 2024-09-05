import datetime
from odoo import models, api,_
from odoo.exceptions import UserError, ValidationError, MissingError
import logging

_logger = logging.getLogger(__name__)

class ReportWeavingOrderBalance(models.AbstractModel):
    _name = 'report.innorug_manufacture.weaving_barcode_insp'
    _description = 'Will Provide the report of all weaving order barcode balance for inspection'

    @api.model
    def _get_report_values(self, docids, data=None):
        sub_data = []
        type_wise = ""
        buyer_name = []
        domain = [('quantity_full_received', '=', False),('state', 'not in', ['cancel']),('is_branch_subcontracting', '=', False)]
        vendor = self.env['res.partner'].sudo().search([('id', '=', int(data.get('subcontractor_id')))])
        if vendor:
            domain+=[('subcontractor_id', '=', vendor.id)]
            type_wise+="Subcontractor Wise Report, "

        date_from = data.get('from_date',False)
        if date_from:
            domain += [('issue_date', '>=', date_from)]
            type_wise+="Date Wise Report"

        date_to = data.get('to_date',False)
        if date_to:
            domain += [('issue_date', '<=', date_to)]

        buyer = int(data.get('buyer',False))
        if buyer:
            vendor = self.env['res.partner'].sudo().search([('id', '=',int(buyer))])
            if vendor:
                buyer_name.append(vendor.name)
                domain+=[('sale_id.partner_id','=',int(vendor.id))]
                type_wise+="Buyer Wise Report, "

        product_group = data.get('product_group',False)
        if product_group:
            domain+=[('jobwork_line_ids.product_id.product_tmpl_id','in',product_group)]
            type_wise+="Product Group Wise Report, "

        product = data.get('product',False)
        if product:
            domain+=[('jobwork_line_ids.product_id','in',product)]
            type_wise+="Product Wise Report, "

        division_ids = data.get('division_id',False)
        if division_ids:
            domain+=[('division_id','in',division_ids)]
            type_wise+="Division Wise Report, "
        
        planing_ids = data.get('planing_ids',False)
        if planing_ids:
            domain+=[('sale_id','in',planing_ids)]
            type_wise+="Planing No. Wise Report, "

        if not self.env.user.division_id:
            raise UserError(_("Please ask your admin to set divisions"))
        else:
            work_orders = self.env['main.jobwork'].sudo().search(domain).filtered(lambda bt: bt.division_id.id in self.env.user.division_id.ids and bt.jobwork_line_ids.filtered(lambda jl: jl.product_qty -jl.return_quantity != jl.received_qty) )
            
            order_type = data.get('order_type',False)
            if order_type:
                order_type = self.env['inno.sale.order.planning'].search([('order_type','=',order_type),('sale_order_id', 'in', work_orders.sale_id.ids)])
                work_orders = work_orders.filtered(lambda wo: wo.sale_id.id in order_type.sale_order_id.ids)
                type_wise+="Order Type Wise Report"
            
            if not work_orders:
                raise UserError(_("Job work not found"))
        # work_orders.jobwork_line_ids.mrp_work_order_id.

        if work_orders and data.get('report_type') == 'weaving_order_barcode_balance_for_inspection':
            self.get_data_by_barcode(work_orders,sub_data)
        elif work_orders and data.get('report_type') == 'weaving_order_product_balance_for_inspection':
            self.get_data_by_product(work_orders, sub_data)
        records = self.env['main.jobwork'].sudo().browse(1)
        if sub_data:

            new_data = {
                        'sub_data': sub_data,'site': 'Main','division':  ', '.join(self.env.user.division_id.mapped('name')) if
                        self.env.user.division_id else 'Main', 
                        'summary' : [{ 'total_qty':sum([line.get('qty') for line in sub_data]),
                        'total_area': sum([line.get('area') for line in sub_data]),}],
                        'total_qty':sum([line.get('qty') for line in sub_data]),
                        'total_area': sum([line.get('area') for line in sub_data]),
                        'to_date': data.get('to_date') if data.get('to_date') else False,
                        'from_date': data.get('from_date') if data.get('from_date') else False, 
                        'division': 'Kelim', 
                        'report_type': data.get('report_type'),
                        'type_wise': type_wise,
                        'buyer':buyer_name[0] if buyer_name else False,
                        'planning_ids': data.get("po_number") if data.get('po_number') else False
                        }
        return {
            'doc_ids': docids,
            'doc_model': 'finishing.work.order',
            'docs': records,
            'data': new_data,}



    def get_data_by_barcode(self, work_orders, sub_data):
        data ={rec.name: rec.id  for rec in (work_orders.subcontractor_id)}
        myKeys = list(data.keys())
        myKeys.sort()
        sorted_dict = {i: data[i] for i in myKeys}
        for key, value in sorted_dict.items():
            sb = self.env['res.partner'].sudo().search([('id', '=', int(value))])
            jobline = work_orders.filtered(lambda sub: sb.id in sub.subcontractor_id.ids)
            bcode = self.env['mrp.barcode']
            for rec in jobline:
                bcode += rec.jobwork_line_ids.barcodes.filtered(lambda st: st.state in [
                '2_allotment', '3_allocated', '6_rejected'] and st.id not in rec.cancelled_barcodes.ids )
            total_area = 0.0
            for rec in bcode:
                total_area += rec.product_id.mrp_area
            sub_data.append({'vendor': f"{sb.name} ({sb.id})", 'mobile': sb.mobile or 'N/A', 'qty' : len(bcode), 'area': total_area,
                             'records': [{'order_no': f"{rec.reference}", 'date': rec.issue_date.strftime('%d/%b/%Y') if rec.issue_date else False, 'due_date': rec.expected_received_date.strftime('%d/%b/%Y') if rec.expected_received_date else False, 'data': [
                                 {'design': pi.name, 'quality': pi.quality.name,
                                  'bcodes': [{'barcode': f"{br.name}", 'bar':4, 'size': br.product_id.inno_mrp_size_id.name, 'pcs': 1} for br in
                                             rec.jobwork_line_ids.barcodes.filtered(lambda st: st.id in bcode.ids and pi.id in st.product_id.product_tmpl_id.ids)]} for pi in
                                 rec.jobwork_line_ids.filtered(
                                     lambda pd: pd.product_qty - pd.return_quantity != pd.received_qty).product_id.product_tmpl_id]} for
                                         rec in work_orders.filtered(lambda sub: sb.id in sub.subcontractor_id.ids)]})

    def get_data_by_product(self, work_orders, sub_data):
        data = {rec.name: rec.id for rec in (work_orders.subcontractor_id)}
        myKeys = list(data.keys())
        myKeys.sort()
        sorted_dict = {i: data[i] for i in myKeys}
        for key, value in sorted_dict.items():
            sb = self.env['res.partner'].sudo().search([('id', '=', int(value))])
            jobline = work_orders.filtered(lambda sub: sb.id in sub.subcontractor_id.ids)
            bcode = self.env['mrp.barcode']
            for rec in jobline:
                bcode += rec.jobwork_line_ids.barcodes.filtered(lambda st: st.state in [
                    '2_allotment', '3_allocated', '6_rejected'] and st.id not in rec.cancelled_barcodes.ids)
            total_area = 0.0
            for rec in bcode:
                total_area += rec.product_id.mrp_area
            sub_data.append({'vendor': f"{sb.name} ({sb.id})", 'mobile': sb.mobile or 'N/A', 'qty' : len(bcode), 'area': total_area,
                             'records': [{'order_no': f"{rec.reference}", 'date': rec.issue_date.strftime('%d/%b/%Y') if rec.issue_date else False, 'due_date': rec.expected_received_date.strftime('%d/%b/%Y') if rec.expected_received_date else False , 'data': [
                                 {'design': pi.name, 'quality': pi.quality.name,
                                  'bcodes': [{'size': pr.product_id.inno_mrp_size_id.name, 'bar':3,'pcs': len(pr.barcodes.filtered(lambda st: st.id in bcode.ids))}for pr in
                                 rec.jobwork_line_ids.filtered(
                                     lambda pd: pd.product_qty - pd.return_quantity != pd.received_qty and pi.id in pd.product_id.product_tmpl_id.ids)]} for pi in
                                 rec.jobwork_line_ids.filtered(
                                     lambda pd: pd.product_qty - pd.return_quantity != pd.received_qty).product_id.product_tmpl_id]} for
                                         rec in work_orders.filtered(lambda sub: sb.id in sub.subcontractor_id.ids)]})
