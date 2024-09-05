import datetime
from odoo import models, api,_
from odoo.exceptions import UserError, ValidationError, MissingError


class ReportMaterialIssue(models.AbstractModel):
    _name = 'report.inno_finishing.report_worker_wise_outstanding_report'
    _description = 'Will Provide the report worker wise outstanding reports'

    @api.model
    def _get_report_values(self, docids, data=None):
        sub_data = []
        new_data = {}
        new_data.update({'to_date': data.get('to_date'),
                     'from_date': data.get('from_date'), })
        domain = []
        date_from = data.get('from_date')
        subcontractor_id = data.get('subcontractor_id')
        if subcontractor_id:
            domain += [('subcontractor_id','=',int(subcontractor_id))]
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
        if data.get('records') == 'operations':
            wo =self.env["mrp.workcenter"].sudo().search([('id', '=', data.get('operation_id'))])
            if work_orders.filtered(lambda op: wo.id in op.operation_id.ids):
                new_data.update({'recors_type': wo.name, 'header' : f"{wo.name} Worker Wise Outstanding Report" })
                self.get_data(work_orders, wo, sub_data)
        records = self.env['finishing.work.order'].sudo().browse(docids)
        if sub_data:
            new_data.update({'sub_data': sub_data, 'total_pcs': sum([rec.get('qty') for rec in sub_data]), 'area': sum([rec.get('area') for rec in sub_data])})
        return {
            'doc_ids': docids,
            'doc_model': 'finishing.work.order',
            'docs': records,
            'data': new_data}

    def get_data(self, work_orders, op,sub_data):
        wo = work_orders.filtered(lambda wo: op.id in wo.operation_id.ids)
        for sb in wo.subcontractor_id:
            sb_order = wo.filtered(lambda wo: sb.id in wo.subcontractor_id.ids)
            record = sb_order.jobwork_barcode_lines.filtered(
                                                lambda st: st.state in ['draft', 'rejected'])
            sub_data.append({'job_worker' : f"{sb.name} {sb.job_worker_code}", 'mobile':  sb.mobile or 'N/A', 'qty': len(record), 'area': sum(record.mapped('total_area')), 'order_date' : [{'date': rec.issue_date} for rec in sb_order]})
