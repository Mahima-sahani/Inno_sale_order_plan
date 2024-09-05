from odoo import fields, models, _,api
from datetime import datetime
from odoo.exceptions import UserError
import requests
import logging
_logger = logging.getLogger(__name__)


class Product(models.Model):
    _inherit = "main.jobwork"

    def get_response_and_update_barcode(self,order):
        response = False
        is_true = False
        try:
            response = requests.get(order, headers={'Accept': 'application/json'}).json()
            idate = False
            ddate = False
            lossQty = False
            print(response)
            if response:
                barcodes = self.env['mrp.barcode'].search([('main_job_work_id', '=', self.id)])
                for res in response:
                    idate = res.get('docDate')
                    ddate = res.get('dueDate')
                    lossQty = res.get('lossQty')
                    bcode=barcodes.filtered(lambda bc: bc.product_id.default_code == res.get('productName') and not bc.old_system_barcode )
                    if bcode:
                        bcode[0].write({'old_system_barcode': res.get('productUidName')})
                        is_true = True
                self.write({'issue_date': idate, 'expected_received_date': ddate,'loss': lossQty})
            return is_true
        except Exception as err:
            _logger.info("......... Error Weaving old Order Update - %r ........!!!!!", err)

    def button_release_components(self):
        call = 'http://192.168.2.125:125/api/WeavingOrderDecSaleOrder/WeavingOrder'
        if not self.branch_id:
            if self.division_id.name == 'KELIM':
                order = call+ f'MainKelim?orderId={self.parallel_order_number}'
                self.get_response_and_update_barcode(order)
            if self.division_id.name == 'KNOTTED':
                order = call + f'MainKnotted?orderId={self.parallel_order_number}'
                self.get_response_and_update_barcode(order)
            if self.division_id.name == 'TUFTED':
                order = call + f'MainTufted?orderId={self.parallel_order_number}'
                is_true=self.get_response_and_update_barcode(order)
                if not is_true:
                    order = call + f'WeavingOrderMainTuftedHandLoom?orderId={self.parallel_order_number}'
                    self.get_response_and_update_barcode(order)
        else:
            if self.branch_id.name == 'FATTUPUR':
                order = call + f'FattupurTufted?orderId={self.parallel_order_number}'
                self.get_response_and_update_barcode(order)
            if self.branch_id.name == 'SARVATKHANI':
                order = call + f'SarwatkhaniTufted?orderId={self.parallel_order_number}'
                self.get_response_and_update_barcode(order)
            if self.branch_id.name == 'CHAKSARI':
                order = call + f'ChaksariTufted?orderId={self.parallel_order_number}'
                self.get_response_and_update_barcode(order)
        barcodes = self.env['mrp.barcode'].search([('main_job_work_id', '=', self.id),('old_system_barcode', '=', False)])
        if not barcodes:
            return super().button_release_components()
        else:
            raise UserError(_("Old barcode number is not mapped please check old order number"))