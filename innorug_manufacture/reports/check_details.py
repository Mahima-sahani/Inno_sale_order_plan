from odoo import models, api
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)

class ReportWeavingCheque(models.AbstractModel):
    _name = 'report.innorug_manufacture.weaving_cheque_details'
    _description = 'Weaving Cheque Details'

    @api.model
    def _get_report_values(self, docids, data=None):
        sub_data = {}
        cheque_detail = []
        docids = data.get('docids')
        records = self.env['account.payment'].browse(docids)
        total_cheque_amt = 0.0

        for rec in records:
            payment_data = {
                'vendor_id': rec.partner_id.id,
                'bill_no': rec.ref,
                'payment_no': rec.name,
                'amount': rec.amount,
                'cheque_no': rec.cheque,
                'date': rec.date,
            }

            total_cheque_amt += rec.amount

            if rec.cheque:
                cheque_detail.append({
                    'partner': rec.partner_id.name,
                    'cheque_no': rec.cheque,
                    'details': payment_data
                })
            else:
                if rec.partner_id.name not in sub_data:
                    sub_data[rec.partner_id.name] = []
                sub_data[rec.partner_id.name].append(payment_data)

        # Compute total amounts
        total_amt = {partner: sum(item['amount'] for item in items) for partner, items in sub_data.items()}
        # total_cheque_amt = {item['cheque_no']: 0 for item in cheque_detail}
        # for item in cheque_detail:
        #     total_cheque_amt[item['cheque_no']] += item['details']['amount']

        new_data = {
            'sub_data': [{'partner': key, 'checks': val} for key, val in sub_data.items()],
            'cheque': cheque_detail,
            'total_amount': total_amt,
            'total_cheque_amount': total_cheque_amt,
            'payment_date': data.get('payment_date'),
        }
        if not records:
            raise UserError("No records found")

        return {
            'doc_ids': docids,
            'doc_model': 'account.payment',
            'docs': records,
            'data': new_data
        }
