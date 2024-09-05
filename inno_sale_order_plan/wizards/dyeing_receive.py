import json

from odoo import models, fields, api, _
from odoo.exceptions import UserError
import requests


class DyeingReceive(models.TransientModel):
    _name = 'dyeing.receive'

    dispatch_no = fields.Char(string='Dispatch Number')

    def confirm_receive(self):
        try:
            response = requests.get(url=f'http://103.70.145.253:125/api/DyeingReceive/DyeingReceive?DisparchNo={self.dispatch_no}')
        except Exception as ex:
            raise UserError(_(ex))
        if response.status_code == 200:
            data = json.loads(response.text)
            if not data:
                raise UserError(_("Data not found for this Dispatch Number !!!"))
            for rec in data:
                dyeing_order = self.env['dyeing.order'].search(['name', '=', rec.get('jobOrderNo')])
                if not dyeing_order:
                    raise UserError(_(f"Dyeing Order ({rec.get('jobOrderNo')}) Not Found."))
                design = self.env['product.template'].search([('name', '=', rec.get('product'))], limit=1)
                if not design:
                    raise UserError(_("Design Not found!!"))
                product_id = False
                if rec.get('shade') in [None, '', False, 'n/a'] and design.product_variant_ids.__len__() == 1:
                    product_id = design.product_variant_ids
                else:
                    product_id = design.product_variant_ids.filtered(
                        lambda pv: pv.product_template_attribute_value_ids.product_attribute_value_id.name == rec.get(
                            'shade'))
                    if not product_id:
                        product_id = design.product_variant_ids.filtered(
                            lambda
                                pv: pv.product_template_attribute_value_ids.product_attribute_value_id.name == rec.get(
                                'shade').strip())
                    if not product_id:
                        raise UserError(_('Product not found !!!'))
                    order_line = dyeing_order.dyeing_order_line_ids.filtered(lambda dy: dy.product_id.id == product_id.id)
                    if not order_line:
                        raise UserError(_("Product not found in order line !!!"))
                    order_line.write({'received_qty': rec.get('receiveQty'), 'qty_to_invoice': rec.get('receiveQty')})
