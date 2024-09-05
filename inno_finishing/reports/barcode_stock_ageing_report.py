from datetime import datetime
from odoo import models, api, _


class ReportStockAgeing(models.AbstractModel):
    _name = 'report.inno_finishing.report_barcode_stock_ageing'
    _description = 'Barcode Based Stock Ageing'

    @api.model
    def _get_report_values(self, docids, data):
        docids = data.get("docids")
        records = self.env['mrp.barcode'].browse(docids)
        barcode_data = records.filtered(lambda rec: rec.state in ["5_verified", '7_finishing'] and rec.finishing_jobwork_id)
        operations = records.mapped('finishing_jobwork_id.operation_id')

        data = []
        for op in operations:
            operation = {op.name: []}
            prod_lst = []
            processed_locations = set()
            for lines in barcode_data:
                issue_date = lines.finishing_jobwork_id.issue_date

                if lines.finishing_jobwork_id.baazar_lines_ids:
                    current_date = lines.finishing_jobwork_id.baazar_lines_ids[-1].date
                else:
                    current_date = datetime.now().date()

                if issue_date:
                    age_days = (current_date - issue_date).days
                else:
                    age_days = 0

                age_category = '0_5' if age_days <= 5 else '6_10' if age_days <= 10 else '11_15' if age_days <= 15 \
                    else '>15' if age_days > 15 else ''

                location_name = lines.location_id.name
                row_data = {
                    'location': location_name if location_name not in processed_locations else '',
                    'product': lines.product_id.name,
                    '0_5': age_days if age_category == '0_5' else 0,
                    '6_10': age_days if age_category == '6_10' else 0,
                    '11_15': age_days if age_category == '11_15' else 0,
                    '>15': age_days if age_category == '>15' else 0,
                }
                row_data['row_count'] = row_data['0_5'] + row_data['6_10'] + row_data['11_15'] + row_data['>15']
                prod_lst.append(row_data)

                processed_locations.add(location_name)

            operation[op.name] = prod_lst
            data.append(operation)

        total_dict = {}
        for rec in data:
            for val, vals in rec.items():
                total_0_5 = sum(entry['0_5'] for entry in vals)
                total_6_10 = sum(entry['6_10'] for entry in vals)
                total_11_15 = sum(entry['11_15'] for entry in vals)
                total_16 = sum(entry['>15'] for entry in vals)
                raw_total = sum(entry['row_count'] for entry in vals)
                total_dict[val] = {'total_0_5': total_0_5, 'total_6_10': total_6_10, 'total_11_15': total_11_15,
                                   'total_16': total_16, 'raw_total': raw_total}

        return {
            'doc_ids': docids,
            'doc_model': 'mrp.barcode',
            'docs': records,
            'data': data,
            'subtotal': total_dict,
        }

    # @api.model
    # def _get_report_values(self, docids, data):
    #     docids = data.get("docids")
    #     records = self.env['mrp.barcode'].browse(docids)
    #     barcode_data = records.filtered(lambda rec: rec.state in ["5_verified",'7_finishing'] and rec.finishing_jobwork_id)[:50]
    #     operations = records.finishing_jobwork_id.operation_id
    #
    #     data = []
    #     for op in operations:
    #         operation = {op.name : []}
    #         prod_lst = []
    #         for lines in barcode_data:
    #             issue_date = lines.finishing_jobwork_id.issue_date
    #
    #             if lines.finishing_jobwork_id.baazar_lines_ids:
    #                 current_date = lines.finishing_jobwork_id.baazar_lines_ids[-1].date
    #             else:
    #                 current_date = datetime.now().date()
    #
    #             if issue_date:
    #                 age_days = (current_date - issue_date).days
    #             else:
    #                 age_days = 0
    #
    #             age_category = '0_5' if age_days <= 5 else '6_10' if age_days <= 10 else '11_15' if age_days <= 15 \
    #                 else '>15' if age_days > 15 else ''
    #
    #             row_data = {
    #                 'location': lines.location_id.name,
    #                 'product': lines.product_id.name,
    #                 '0_5': 1 if age_category == '0_5' else 0,
    #                 '6_10': 1 if age_category == '6_10' else 0,
    #                 '11_15': 1 if age_category == '11_15' else 0,
    #                 '>15': 1 if age_category == '>15' else 0,
    #             }
    #             row_data['row_count'] = row_data['0_5'] + row_data['6_10'] + row_data['11_15'] + row_data['>15']
    #             prod_lst.append(row_data)
    #
    #         operation[op.name] = prod_lst
    #         data.append(operation)
    #
    #     total_dict = {}
    #     for rec in data:
    #         for val, vals in rec.items():
    #             total_0_5 =  sum(entry['0_5'] for entry in vals)
    #             total_6_10 =  sum(entry['6_10'] for entry in vals)
    #             total_11_15 =  sum(entry['11_15'] for entry in vals)
    #             total_16 =  sum(entry['>15'] for entry in vals)
    #             raw_total = sum(entry['row_count'] for entry in vals)
    #             total_dict[val] = {'total_0_5': total_0_5, 'total_6_10': total_6_10, 'total_11_15': total_11_15,
    #                                'total_16': total_16, 'raw_total': raw_total}
    #
    #     return {
    #         'doc_ids': docids,
    #         'doc_model': 'mrp.barcode',
    #         'docs': records,
    #         'data': data,
    #         'subtotal': total_dict,
    #     }
