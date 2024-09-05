from odoo import models, fields, _
from odoo.exceptions import UserError
import base64


class SaleOrderPlanning(models.Model):
    _inherit = 'inno.sale.order.planning'

    def manger_authentication(self):
        self.env["inno.migration.record"].with_context(update_planning=True, order=self).update_size_bom_and_sku()
        self.update_mrp_size()
        designs = self.sale_order_planning_lines.product_id.product_tmpl_id.filtered(lambda prd: not prd.is_verified)
        for design in designs:
            verification = self.env['inno.product.verification'].search([('product_id', '=', design.id)], limit=1)
            if not verification:
                bom = design.bom_ids.filtered(lambda bom: bom.product_tmpl_id and not bom.product_id)
                self.env['inno.product.verification'].sudo().create({
                    'product_id': design.id, 'priority': 'urgent', 'bom_id': bom.id})
            else:
                verification.sudo().write({'priority': 'urgent'})
            self._cr.commit()
        if designs:
            data = designs.bom_ids.filtered(lambda bom: bom.product_tmpl_id and not bom.product_id).ids
            pdf = self.env.ref('inno_data_verification.action_report_for_design_bom', raise_if_not_found=False
                               ).sudo()._render_qweb_pdf('inno_data_verification.action_report_for_design_bom',
                                                                                 res_ids=data)[0]
            pdf = base64.b64encode(pdf).decode()
            attachment = self.env['ir.attachment'].create({
                'name': f"Design BOM Data", 'type': 'binary', 'datas': pdf,
                'res_model': 'inno.sale.order.planning', 'res_id': self.id})
            self.message_post(body="<b>Product Planning report</b>", attachment_ids=[attachment.id])
            self._cr.commit()
            raise UserError(_("Please Verify the data of the Products First."))
        return super().manger_authentication()


class SaleIRModel(models.Model):
    _inherit = 'ir.model.fields'
