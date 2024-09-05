from odoo import models, fields, api
from odoo.modules import get_resource_path
import base64


class PrintLabels(models.TransientModel):
    _name = 'inno.print.package.label'
    _description = 'print different labels'

    label_type = fields.Selection(selection=[('sci_label', 'SCI Label'), ('custom', 'Custom Label'),
                                             ('hospitality', 'Hospitality')])
    sample_image = fields.Binary(store=False)

    @api.onchange('label_type')
    def onchange_label_type(self):
        img_res = get_resource_path('inno_packaging', 'data', f'{self.label_type}.jpg')
        if img_res:
            sample_img = base64.b64encode(open(img_res, 'rb').read())
            self.sample_image = sample_img if sample_img else False
        else:
            self.sample_image = False

    def print_package_label(self):
        if self.label_type == 'sci_label':
            return self.env.ref('inno_packaging.action_report_print_package_label',
                                raise_if_not_found=False).report_action(docids=self._context.get('active_ids'))
        elif self.label_type == 'custom':
            return self.env.ref('inno_packaging.action_report_print_custom_label',
                                raise_if_not_found=False).report_action(docids=self._context.get('active_ids'))
        elif self.label_type == 'hospitality':
            return self.env.ref('inno_packaging.action_report_print_hospitality_label',
                                raise_if_not_found=False).report_action(docids=self._context.get('active_ids'))
        elif self.label_type == 'surya_qr':
            return self.env.ref('inno_packaging.action_report_print_surya_qr_label',
                                raise_if_not_found=False).report_action(docids=self._context.get('active_ids'))
        elif self.label_type == 'upc_label':
            return self.env.ref('inno_packaging.action_report_print_upc_label',
                                raise_if_not_found=False).report_action(docids=self._context.get('active_ids'))
        elif self.label_type == 'sci_custom':
            return self.env.ref('inno_packaging.action_report_print_sci_custom_label',
                                raise_if_not_found=False).report_action(docids=self._context.get('active_ids'))
        elif self.label_type == 'livabliss':
            return self.env.ref('inno_packaging.action_report_print_livabliss_label',
                                raise_if_not_found=False).report_action(docids=self._context.get('active_ids'))
        elif self.label_type == 'livabliss':
            return self.env.ref('inno_packaging.action_report_print_livabliss_upc_label',
                                raise_if_not_found=False).report_action(docids=self._context.get('active_ids'))
        else:
            return False
