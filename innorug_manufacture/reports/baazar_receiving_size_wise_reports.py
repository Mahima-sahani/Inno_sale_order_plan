import datetime
from odoo import models, api, _
from odoo.exceptions import UserError, ValidationError, MissingError


class ReportWeavingOrderBalance(models.AbstractModel):
    _name = 'report.innorug_manufacture.weaving_barcode_insp_baazar_size'
    _description = 'Will Provide the report of all weaving order barcode balance for inspection'

    @api.model
    def _get_report_values(self, docids, data=None):
        sub_data = []
        new_data = {}
        domain = []
        baazar_lines = False
        vendor = self.env['res.partner'].sudo().search([('id', '=', int(data.get('subcontractor_id')))])
        buyer = self.env['res.partner'].sudo().search([('id', '=', int(data.get('buyer_id')))])
        plannings = self.env['sale.order'].sudo().search([('id', 'in', data.get('po_no'))])
        product = self.env['product.product'].sudo().search([('id', 'in', data.get('product_id'))])
        product_group = self.env['product.template'].sudo().search([('id', 'in', data.get('product_group'))])
        branch_id = self.env['weaving.branch'].sudo().search([('id', '=', int(data.get('branch_id')))])
        is_branch = data.get('include_branch')
        exclude_branch = data.get('exclude_branch')
        date_from = data.get('from_date')
        work_orders = self.env['main.baazar'].sudo().search([])
        if date_from:
            domain += [('date', '>=', date_from)]
        date_to = data.get('to_date')
        if date_to:
            domain += [('date', '<=', date_to)]
            work_orders = self.env['main.baazar'].sudo().search(domain)
        if not is_branch:
            baazar_lines = work_orders.baazar_lines_ids.filtered(lambda bl: not bl.main_jobwork_id.is_branch_subcontracting)

        if plannings:
            baazar_lines = work_orders.baazar_lines_ids.filtered(
                lambda bl: bl.barcode.sale_id.id in plannings.ids and bl.state in ['verified', ])
        if product:
            baazar_lines = work_orders.baazar_lines_ids.filtered(
                lambda bl: bl.product_id.id in product.ids and bl.state in ['verified', ])
        if product_group:
            baazar_lines = work_orders.baazar_lines_ids.filtered(
                lambda bl: bl.product_id.product_tmpl_id.id in product_group.ids and bl.state in ['verified', ])
        if buyer:
            baazar_lines = work_orders.baazar_lines_ids.filtered(
                lambda bl: bl.barcode.sale_id.partner_id.id in buyer.ids and bl.state in ['verified', ])
        if vendor:
            baazar_lines = work_orders.baazar_lines_ids.filtered(
                lambda bl: bl.bazaar_id.subcontractor_id.id in vendor.ids and bl.state in ['verified', ])
        brnch_order = work_orders
        # if not is_branch:
        #     baazar_lines = work_orders.baazar_lines_ids.filtered(
        #         lambda wo: not wo.main_jobwork_id.is_branch_subcontracting and not wo.main_jobwork_id.branch_id)
        if exclude_branch:
            baazar_lines = brnch_order.baazar_lines_ids.filtered(
                lambda bl: bl.main_jobwork_id.branch_id)
        if branch_id:
            baazar_lines = brnch_order.baazar_lines_ids.filtered(
                lambda bl: branch_id.id in bl.main_jobwork_id.branch_id.ids)
        if baazar_lines:
            new_data.update({'to_date': data.get('to_date'),
                             'from_date': data.get('from_date')})
            self.get_data_by_product(
                baazar_lines.bazaar_id.filtered(lambda bt: bt.division_id.id in self.env.user.division_id.ids),
                sub_data, data,baazar_lines)
        else:
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
                                 'from_date': data.get('from_date'), 'division': 'Kelim',
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
                work_orders = self.env['main.baazar'].sudo().search(domain).filtered(
                    lambda bt: bt.division_id.id in self.env.user.division_id.ids and bt.baazar_lines_ids.filtered(
                        lambda bl: bl.state in ['verified', ]))
                if work_orders:
                    if is_branch == 'True':
                        work_orders = work_orders.filtered(lambda wo: wo.main_jobwork_id.is_branch_subcontracting and wo.main_jobwork_id.branch_id)
                    else:
                        work_orders = work_orders.filtered(
                            lambda wo: not wo.main_jobwork_id.is_branch_subcontracting and not wo.main_jobwork_id.branch_id)
                if not work_orders:
                    raise UserError(_("Job work not found"))
            if work_orders and data.get('report_type') == 'baazar_repots':
                self.get_data_by_product(work_orders, sub_data, data,baazar=False)
        records = self.env['main.baazar'].sudo().browse(1)
        if sub_data and work_orders:
            new_data.update({'sub_data': sub_data, 'total_pcs': sum([rec.get('total_pcs') for rec in sub_data]),
                             'division': ', '.join(self.env.user.division_id.mapped('name')) if
                             self.env.user.division_id else 'Main', 'site': 'Main',
                             'with_barcode': data.get('with_barcode'),
                             'rec': f"{', '.join(plannings.mapped('order_no'))},{', '.join(product.mapped('default_code'))},{', '.join(product_group.mapped('name'))},{', '.join(buyer.mapped('name'))}",
                             'total_area': round(sum([rec.get('total_area') for rec in sub_data]), 4),
                             'total_Weight': round(sum([rec.get('total_Weight') for rec in sub_data]), 4),
                             'total_amount': round(sum([rec.get('total_amount') for rec in sub_data]), 4),
                             'qa_incentive': round(sum([rec.get('qa_incentive') for rec in sub_data]), 4),
                             'total_incentive': round(sum([rec.get('incentive') for rec in sub_data]), 4),
                             'QA_Penalty': round(sum([rec.get('QA_Penalty') for rec in sub_data]), 4),
                             'total_Net_Payable': round(sum([rec.get('total_Net_Payable') for rec in sub_data]), 4), })
        return {
            'doc_ids': docids,
            'doc_model': 'finishing.work.order',
            'docs': records,
            'data': new_data, }

    def get_data_by_product(self, work_orders, sub_data,data, baazar=False):
        for sn in work_orders.subcontractor_id:
            baazar_lines = False
            for sb in work_orders.filtered(lambda ln: ln.baazar_lines_ids and ln.subcontractor_id == sn):
                if baazar:
                    baazar_lines = sb.baazar_lines_ids.filtered(
                        lambda bl: bl.state in ['verified', ] and bl.id in baazar.ids)
                else:
                    baazar_lines = sb.baazar_lines_ids.filtered(lambda bl: bl.state in ['verified', ])
                if baazar_lines:
                    area = 0.0
                    weight = 0.0
                    incentive = sum(
                        [line.job_work_id.incentive * line.product_id.mrp_area for
                         line in sb.baazar_lines_ids if line.state == 'verified'])
                    amount = sum(
                        [line.job_work_id.rate * line.product_id.mrp_area for
                         line in sb.baazar_lines_ids if line.state == 'verified'])
                    qa_penality = 0.00
                    for ar in baazar_lines:
                        area += ar.product_id.mrp_area
                        weight += float(ar.actual_weight)
                        if ar.is_full_penalty:
                            qa_penality += ar.penalty
                        else:
                            qa_penality += ar.penalty * ar.product_id.mrp_area
                    qa_incentive = round(sum(baazar_lines.barcode.pen_inc_ids.filtered(
                        lambda
                            pi: pi.type == 'incentive' and pi.rec_id in baazar_lines.main_jobwork_id.ids and pi.model_id == self.env.ref(
                            'innorug_manufacture.model_main_jobwork')).mapped('amount')), 2)
                    net_payble = (amount + incentive + qa_incentive) - qa_penality
                    sub_data.append({'vendor': f"{sb.subcontractor_id.name} ({sb.subcontractor_id.id})",
                                     'order': sb.main_jobwork_id.reference, 'total_pcs': len(baazar_lines),
                                     'total_area': round(area, 4),
                                     'total_Weight': round(weight, 4), 'total_amount': amount,
                                     'with_barcode': data.get('with_barcode'),
                                     'qa_incentive': qa_incentive,
                                     'QA_Penalty': qa_penality, 'total_Net_Payable': net_payble, 'incentive': incentive,
                                     'receive_no': sb.reference or 'N/A',
                                     'date': sb.date.strftime('%d/%b/%Y') if sb.date else False,
                                     'records': [{'quality': rec.product_tmpl_id.quality.name, 'design': rec.name,
                                                  'size': rec.inno_mrp_size_id.name,
                                                  'pcs': len(
                                                      baazar_lines.filtered(lambda ln: rec.id in ln.product_id.ids)),
                                                  'area': rec.mrp_area * len(
                                                      baazar_lines.filtered(lambda ln: rec.id in ln.product_id.ids)),
                                                  'weight': round(sum([ln.actual_weight for ln in baazar_lines.filtered(
                                                      lambda bl: rec.id in bl.product_id.ids)]), 4),
                                                  'rate': sb.main_jobwork_id.jobwork_line_ids.filtered(
                                                      lambda ln: rec.id in ln.product_id.ids).mapped('rate')[
                                                      0] if sb.main_jobwork_id.jobwork_line_ids.filtered(
                                                      lambda ln: rec.id in ln.product_id.ids).mapped('rate') else 0,
                                                  'inc': sb.main_jobwork_id.jobwork_line_ids.filtered(
                                                      lambda ln: rec.id in ln.product_id.ids).mapped('incentive')[
                                                      0] if sb.main_jobwork_id.jobwork_line_ids.filtered(
                                                      lambda ln: rec.id in ln.product_id.ids).mapped(
                                                      'incentive') else '-',
                                                  'amount': (rec.mrp_area * len(
                                                      baazar_lines.filtered(
                                                          lambda ln: rec.id in ln.product_id.ids))) * (
                                                                sb.main_jobwork_id.jobwork_line_ids.filtered(
                                                                    lambda ln: rec.id in ln.product_id.ids).mapped(
                                                                    'rate')[
                                                                    0] if sb.main_jobwork_id.jobwork_line_ids.filtered(
                                                                    lambda ln: rec.id in ln.product_id.ids).mapped(
                                                                    'rate') else 0),
                                                  'qa_incentive': round(sum((baazar_lines.filtered(
                                                      lambda
                                                          ln: rec.id in ln.product_id.ids)).barcode.pen_inc_ids.filtered(
                                                      lambda
                                                          pi: pi.type == 'incentive' and pi.rec_id in baazar_lines.main_jobwork_id.ids and pi.model_id == self.env.ref(
                                                          'innorug_manufacture.model_main_jobwork')).mapped('amount')),
                                                                        2),
                                                  'qa_panality': self.get_full_penality(baazar_lines,rec),
                                                  'net_payble': self.get_nayble_amount(rec, baazar_lines, sb),
                                                  'barcodes': ', '.join((baazar_lines.filtered(
                                                      lambda ln: rec.id in ln.product_id.ids)).barcode.mapped('name')),
                                                  'status':
                                                      baazar_lines.filtered(lambda ln: rec.id in ln.product_id.ids)[
                                                          0].state, } for rec in baazar_lines.product_id], })

    def get_full_penality(self,baazar_lines, rec):
        amt = 0.00
        for rec in baazar_lines.filtered(lambda ln: rec.id in ln.product_id.ids):
            if rec.is_full_penalty:
                amt += rec.penalty
            else:
                amt += rec.penalty * rec.product_id.mrp_area
        return round(amt, 3)

    def get_nayble_amount(self, rec, baazar_lines, sb):
        total_area = rec.mrp_area * len(baazar_lines.filtered(lambda ln: rec.id in ln.product_id.ids))
        amount_with_incenctive = total_area * sb.main_jobwork_id.jobwork_line_ids.filtered(
            lambda ln: rec.id in ln.product_id.ids).mapped('incentive')[
            0] if sb.main_jobwork_id.jobwork_line_ids.filtered(
            lambda ln: rec.id in ln.product_id.ids).mapped('incentive') else 0
        amount_with_rate = total_area * sb.main_jobwork_id.jobwork_line_ids.filtered(
            lambda ln: rec.id in ln.product_id.ids).mapped('rate')[
            0] if sb.main_jobwork_id.jobwork_line_ids.filtered(
            lambda ln: rec.id in ln.product_id.ids).mapped('rate') else 0
        net_payble_amount = (amount_with_rate + amount_with_incenctive) - self.get_full_penality(baazar_lines,rec)
        return net_payble_amount
