import datetime
from odoo import models, api, _
from odoo.exceptions import UserError, ValidationError, MissingError


class ReportWeavingOrderBalance(models.AbstractModel):
    _name = 'report.inno_finishing.finishing_receive_report'
    _description = 'Will Provide the report of all weaving order barcode balance for inspection'

    @api.model
    def _get_report_values(self, docids, data=None):
        sub_data = []
        new_data = {}
        vendor = self.env['res.partner'].sudo().search([('id', '=', int(data.get('vendor')))])
        operation = self.env['mrp.workcenter'].sudo().search([('id', '=', int(data.get('operation_id')))])
        baazr_id = self.env['finishing.baazar'].sudo().search([('id', '=', int(data.get('finishing_baazar_id')))])
        date_from = data.get('date')
        baazar = False
        if baazr_id:
            baazar = baazr_id
        elif vendor and operation and date_from:
            baazar = self.env['finishing.baazar'].sudo().search(
                [('date', '=', date_from), ('subcontractor_id', '=', vendor.id)]).filtered(
                lambda fn: fn.finishing_work_id.operation_id.id == operation.id)
        if baazar:
            self.get_data_by_baazar(baazar, sub_data)
            size = [{
                'size': jobwork.name,
                'qty': len(
                    baazar.jobwork_received_ids.filtered(lambda ln: ln.inno_finishing_size_id.id in jobwork.ids))
            } for jobwork in baazar.jobwork_received_ids.inno_finishing_size_id]
            temp_len = len(size)
            lis1, lis2, lis3 = [], [], []
            while temp_len > 0:
                lis1.append(size.pop())
                temp_len -= 1
                if temp_len == 0:
                    break
                lis2.append(size.pop())
                temp_len -= 1
                if temp_len == 0:
                    break
                lis3.append(size.pop())
                temp_len -= 1
            new_data.update({'size1': lis1, 'size2': lis2, 'size3': lis3, })
        if not baazar:
            raise UserError(_("Job work not found"))
        records = self.env['finishing.work.order'].sudo().browse(1)
        unit = {'sq_yard': 'Sq. Yard',
                'feet': 'Feet',
                'sq_feet': 'Sq. Feet',
                'choti': 'Sq. Meter', }
        if sub_data:
            new_data.update({'sub_data': sub_data,
                             'header': f"{baazar.finishing_work_id.operation_id.name if baazar else operation.name} Receive Challan",
                             'area_in_feet': f"{round(sum([rec.product_id.inno_finishing_size_id.area for rec in baazar.jobwork_received_ids]), 3)} 'SQ.Feet" ,
                             'area': f"{round(sum(baazar.jobwork_received_ids.mapped('total_area')), 4)} {unit.get(baazar.jobwork_received_ids[0].unit)}" if baazar else 0,
                             'pcs': len(baazar.jobwork_received_ids) if baazar else 0,
                             'penality': round(sum(baazar.jobwork_received_ids.mapped('penalty')), 3)})
        return {
            'doc_ids': docids,
            'doc_model': 'finishing.work.order',
            'docs': records,
            'data': new_data, }

    def get_data_by_baazar(self, baazar, sub_data):
        sub_data.append({
            'vendor': baazar[0].subcontractor_id.name, 'Code': baazar[0].subcontractor_id.id,
            'GSTIN': baazar[0].subcontractor_id.vat, 'Address': baazar[0].subcontractor_id.street,
            'Mobile': baazar[0].subcontractor_id.mobile,
            'Receive Date': baazar[0].date.strftime('%d/%b/%Y') if baazar[0].date else False,
            'Godown': baazar[0].location_id.warehouse_id.name
            , 'Receive By': '', 'data': [
                {'receive_no': rec.reference, 'order_no': rec.finishing_work_id.name,
                 'order_date': rec.finishing_work_id.issue_date.strftime(
                     '%d/%b/%Y') if rec.finishing_work_id.issue_date else False, 'lines': [
                    {'design': line.product_id.product_tmpl_id.name,
                     'hsn': line.product_id.product_tmpl_id.l10n_in_hsn_code, 'size': line.inno_finishing_size_id.name,
                     'pcs': 1, 'penality': line.penalty,
                     'barcode': line.barcode_id.name, 'status': line.state} for line in rec.jobwork_received_ids]} for
                rec in baazar]
        })
