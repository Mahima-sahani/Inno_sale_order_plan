import datetime
from odoo import models, api, _
from odoo.exceptions import UserError, ValidationError, MissingError


class ReportFinishngBaazar(models.AbstractModel):
    _name = 'report.inno_finishing.finsihing_baazar_reports'
    _description = 'Will Provide the report of all finishing payment advice'

    @api.model
    def _get_report_values(self, docids, data=None):
        sub_data = []
        new_data = {}
        domain = []
        vendor = self.env['res.partner'].sudo().search([('id', '=', int(data.get('subcontractor_id')))])
        operation_id = self.env['mrp.workcenter'].sudo().search([('id', '=', int(data.get('operation')))])
        if vendor:
            new_data.update({'to_date': False,
                             'from_date': False, 'division': 'Kelim',
                             'report_type': data.get('report_type')})
            date_from = data.get('from_date')
            if date_from:
                domain += [('date', '>=', date_from)]
            date_to = data.get('to_date')
            if date_to:
                domain += [('date', '<=', date_to)]
            domain += [('subcontractor_id', '=', vendor.id)]
        else:
            new_data.update({'to_date': data.get('to_date'),
                             'from_date': data.get('from_date'),
                             'report_type': data.get('report_type')})
            date_from = data.get('from_date')
            if date_from:
                domain += [('date', '>=', date_from)]
            date_to = data.get('to_date')
            if date_to:
                domain += [('date', '<=', date_to)]
        if not self.env.user.division_id:
            raise UserError(_("Please ask your admin to set divisions"))
        else:
            work_orders = self.env['finishing.baazar'].sudo().search(domain).filtered(
                lambda
                    bt: bt.division_id.id in self.env.user.division_id.ids and bt.finishing_work_id.operation_id.id == operation_id.id and bt.jobwork_received_ids.filtered(
                    lambda bl: bl.state in ['verified', ]))
            if not work_orders:
                raise UserError(_("Job work not found"))
        if work_orders and data.get('report_type') == 'receive_reports':
            self.get_data_by_product(work_orders, sub_data,data)
        records = self.env['finishing.baazar'].sudo().browse(1)
        if sub_data and work_orders:
            new_data.update({'sub_data': sub_data,
                             'header': f"{operation_id.name} Receive Register",
                             'with_barcode': data.get('with_barcode'),
                             # 'total_pcs': sum([rec.get('total_pcs') for rec in sub_data])

                             'division': ', '.join(self.env.user.division_id.mapped('name')) if
                             self.env.user.division_id else 'Main', 'site': 'Main',
                             'summary': [{
                                 'total_area': round(sum([rec.get('area') for rec in sub_data]), 4),
                                 'total_amount': round(sum([rec.get('total_amount') for rec in sub_data]), 2),
                                 'total_pcs': sum([rec.get('pcs') for rec in sub_data]),
                                 'fix_incentive': round(sum([rec.get('fix_inc') for rec in sub_data]), 2),
                                 'qa_incentive': round(sum([rec.get('qa_inc') for rec in sub_data]), 2),
                                 'QA_Penalty': round(sum([rec.get('qa_penality') for rec in sub_data]), 2),
                                 'total_Net_Payable': round(sum([rec.get('net_pable') for rec in sub_data]), 2)}],
                             })
        return {
            'doc_ids': docids,
            'doc_model': 'finishing.work.order',
            'docs': records,
            'data': new_data, }

    def get_data_by_product(self, work_orders, sub_data,data):
        for sb in work_orders.filtered(lambda ln: ln.jobwork_received_ids).subcontractor_id:
            receives_ids = work_orders.filtered(
                lambda bl: bl.subcontractor_id.id == sb.id and bl.jobwork_received_ids.filtered(
                    lambda bl: bl.state in ['verified', ]))
            verified_lines = receives_ids.jobwork_received_ids.filtered(
                lambda bl: bl.state in ['verified', ])
            unit = {'sq_yard': 'Sq. Yard',
                    'feet': 'Feet',
                    'sq_feet': 'Sq. Feet',
                    'choti': 'Sq. Meter', }
            sub_data.append(
                {'vendor': sb.name, 'gst': sb.vat, 'area': round(sum([rec.total_area for rec in verified_lines]), 4),
                 'pcs': len(verified_lines),
                 'fix_inc': round(sum([rec.total_area * rec.fixed_incentive for rec in verified_lines]), 2),
                 'qa_inc': round(sum([rec.incentive for rec in verified_lines]), 2),
                 'with_barcode': data.get('with_barcode'),
                 'total_amount': round(
                     sum([(rec.total_area * rec.rate) + (rec.total_area * rec.fixed_incentive) + rec.incentive for rec
                          in
                          verified_lines]), 2),
                 'qa_penality': round(sum([rec.penalty for rec in verified_lines]), 2), 'net_pable': round(
                    sum([(rec.total_area * rec.rate) + (
                            rec.total_area * rec.fixed_incentive) + rec.incentive - rec.penalty for rec in
                         verified_lines]), 2),
                 'record': [
                     {'receive_no': rec.reference, 'order_no': rec.finishing_work_id.name,
                      'receive_date': rec.date.strftime('%d/%m/%Y') if rec.date else False,
                      'data': [
                          {'product': rc.default_code, 'size': rc.inno_finishing_size_id.name, 'area': round(
                              sum([ar.total_area for ar in rec.jobwork_received_ids.filtered(
                                  lambda bl: bl.state in ['verified', ] and bl.product_id.id == rc.id)]), 4),
                           'unit': unit.get(rec.jobwork_received_ids.filtered(
                               lambda bl: bl.state in ['verified', ] and bl.product_id.id == rc.id)[0].unit),
                           'qty': len(rec.jobwork_received_ids.filtered(
                               lambda bl: bl.state in ['verified', ] and bl.product_id.id == rc.id)),
                           'rate': rec.jobwork_received_ids.filtered(
                               lambda bl: bl.state in ['verified', ] and bl.product_id.id == rc.id)[0].rate,
                           'fix_inc': round(
                               sum([ar.total_area * ar.fixed_incentive for ar in
                                    rec.jobwork_received_ids.filtered(
                                        lambda bl: bl.state in ['verified', ] and bl.product_id.id == rc.id)]),
                               2),
                           'qa_inc': round(
                               sum([ar.incentive for ar in rec.jobwork_received_ids.filtered(
                                   lambda bl: bl.state in ['verified', ] and bl.product_id.id == rc.id)]), 2),
                           'amount': self.calculate_total_amount(rec, rc, pay=False, penality=False,
                                                                 amount=True),
                           'penality': self.calculate_total_amount(rec, rc, pay=False, penality=True,
                                                                   amount=False),
                           'net_payble': self.calculate_total_amount(rec, rc, pay=True, penality=False,
                                                                     amount=False),
                           'barcode': ', '.join(rec.jobwork_received_ids.filtered(
                               lambda bl: bl.state in [
                                   'verified', ] and bl.product_id.id == rc.id).barcode_id.mapped('name')),
                           'status': 'Verified'} for rc in
                          rec.jobwork_received_ids.filtered(
                              lambda bl: bl.state in ['verified', ]).product_id]} for rec in receives_ids if
                     rec.jobwork_received_ids.filtered(lambda bl: bl.state in ['verified', ])]})

    def calculate_total_amount(self, rec, rc, pay=False, penality=False, amount=False):
        qa_incentive = round(
            sum([ar.incentive for ar in rec.jobwork_received_ids.filtered(
                lambda bl: bl.state in ['verified', ] and bl.product_id.id == rc.id)]), 2)
        fix_incentive = round(sum([ar.total_area * ar.fixed_incentive for ar in rec.jobwork_received_ids.filtered(
            lambda bl: bl.state in ['verified', ] and bl.product_id.id == rc.id)]), 2)
        sub_total_amount = round(sum([ar.total_area * ar.rate for ar in rec.jobwork_received_ids.filtered(
            lambda bl: bl.state in ['verified', ] and bl.product_id.id == rc.id)]), 2)
        penalty = round(sum([ar.penalty for ar in rec.jobwork_received_ids.filtered(
            lambda bl: bl.state in ['verified', ] and bl.product_id.id == rc.id)]), 2)
        if amount:
            return qa_incentive + fix_incentive + sub_total_amount
        if pay:
            return (qa_incentive + fix_incentive + sub_total_amount) - penalty
        if penality:
            return penalty
