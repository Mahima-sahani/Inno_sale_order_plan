import datetime
from odoo import models, api, _
from odoo.exceptions import UserError, ValidationError, MissingError


class ReportPurchaseIndent(models.AbstractModel):
    _name = 'report.inno_purchase.report_purchase_indent'
    _description = 'Will Provide the report worker wise outstanding reports'

    @api.model
    def _get_report_values(self, docids, data=None):
        new_data = {}
        records = self.env['inno.purchase'].sudo().browse(docids)
        sub_data = [
            {'product': f"{rec.product_id.name} Group-{rec.product_id.product_tmpl_id.raw_material_group}",
             'plan_qty': rec.product_qty, 'unit': rec.uom_id.name,
             'remark': rec.remarks, } for rec in records.inno_purchase_line if rec.product_id]
        if records:
            new_data.update({'plan_no': records.reference, 'Plan_date': records.issue_date,
                             'Due_date': records.expected_received_date,})
        new_data.update({'sub_data': sub_data,
                         'total_qty': sum([rec.get('plan_qty') for rec in sub_data])})
        return {
            'doc_ids': docids,
            'doc_model': 'inno.purchase',
            'docs': records,
            'data': new_data}
