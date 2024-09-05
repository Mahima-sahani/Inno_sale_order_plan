import datetime
from odoo import models, api,_
from odoo.exceptions import UserError, ValidationError, MissingError


class ReportMaterialIssue(models.AbstractModel):
    _name = 'report.inno_finishing.report_barcode_wise_order_summary'
    _description = 'Will Provide the report of all the received Barcodes'

    @api.model
    def _get_report_values(self, docids, data=None):
        sub_data = []
        new_data = {}
        new_data.update({'to_date': data.get('to_date'),
                     'from_date': data.get('from_date'), })
        domain = []
        subcontractor_id = data.get('subcontractor_id')
        if subcontractor_id:
            domain+=[('subcontractor_id','=',int(subcontractor_id))]
        date_from = data.get('from_date')
        if date_from:
            domain += [('issue_date', '>=', date_from)]
        date_to = data.get('to_date')
        if date_to:
            domain += [('issue_date', '<=', date_to)]
            domain += [('status', 'not in', ['done','cancel','return'])]
        if not self.env.user.division_id:
            raise UserError(_("Please ask your admin to set divisions"))
        else:
            work_orders = self.env['finishing.work.order'].sudo().search(domain).filtered(lambda st: st.division_id.id in self.env.user.division_id.ids and st.jobwork_barcode_lines.filtered(lambda st: st.state in ['draft','rejected']))
        if data.get('records') == 'all':
            operations = work_orders.operation_id
            new_data.update({'recors_type': "ALL", 'header' : f"Barcode Wise Finishing Order Balance"})
            for op in operations:
                self.get_data( work_orders, op,sub_data)
        elif data.get('records') == 'operations':
            wo =self.env["mrp.workcenter"].sudo().search([('id', '=', data.get('operation_id'))])
            if work_orders.filtered(lambda op: wo.id in op.operation_id.ids):
                new_data.update({'recors_type': wo.name, 'header' : f"Barcode Wise {wo.name} Order Balance" })
                self.get_data(work_orders, wo, sub_data)
        records = self.env['finishing.work.order'].sudo().browse(docids)
        if sub_data:
            new_data.update({'sub_data': sub_data,})
        return {
            'doc_ids': docids,
            'doc_model': 'finishing.work.order',
            'docs': records,
            'data': new_data}

    def get_data(self, work_orders, op,sub_data):
        wo = work_orders.filtered(lambda wo: op.id in wo.operation_id.ids)
        for sb in wo.subcontractor_id:
            sb_order = wo.filtered(lambda wo: sb.id in wo.subcontractor_id.ids)
            unit = {'sq_yard': 'Sq. Yard',
                    'feet': 'Feet',
                    'sq_feet': 'Sq. Feet',
                    'choti': 'Sq. Meter', }
            sub_data.append(
                {'operation': op.name, 'units': unit.get(sb_order.jobwork_barcode_lines[0].unit),
                 'sub_data': [{'subcontractor': sb.name,
                               'records': [{'date': rec.issue_date, 'order_name': rec.name,
                                            'data': [{
                                                'product': pd.default_code, 'pcs': len((
                                                                                           rec.jobwork_barcode_lines.filtered(
                                                                                               lambda
                                                                                                   code: pd.id in code.product_id.ids and code.state in [
                                                                                                   'draft',
                                                                                                   'rejected']))),
                                                'area':  rec.jobwork_barcode_lines.filtered(
                                                    lambda code: pd.id in code.product_id.ids)[0].total_area,
                                                'barcode': ', '.join((rec.jobwork_barcode_lines.filtered(
                                                    lambda code: pd.id in code.product_id.ids and code.state in [
                                                        'draft', 'rejected'])).barcode_id.mapped('name')),
                                                'size': pd.inno_finishing_size_id.name,
                                            } for pd in rec.jobwork_barcode_lines.filtered(
                                                lambda st: st.state in ['draft', 'rejected']).product_id]} for rec in
                                           sb_order]}]})
