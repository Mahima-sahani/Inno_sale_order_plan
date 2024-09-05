from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError, MissingError


class InnoUpdateRate(models.TransientModel):
    _name = 'inno.sample.rate.update'

    rate = fields.Float(digits=(8, 3), string='Add Rate')
    is_size_wize = fields.Boolean("Size Wize")
    product_tmpl_id = fields.Many2one(comodel_name="product.template", string="Design")
    inno_sizewise_rate_update_line = fields.One2many("inno.sizewise.rate.update", 'inno_sample_rate_update_id',
                                                     string="Size Wize")
    finishing_work_id = fields.Many2one(comodel_name="finishing.work.order", readonly="1")

    @api.model
    def default_get(self, fields_list):
        rec = super().default_get(fields_list)
        order = self.env['finishing.work.order'].browse(self._context.get('active_id'))
        if order:
            line = [(0, 0, {'size_id': rec.inno_finishing_size_id.id,
                            'rate': order.jobwork_barcode_lines.filtered(lambda pr: pr.product_id.id in rec.ids)[
                                0].rate,
                            'unit': order.jobwork_barcode_lines.filtered(lambda pr: pr.product_id.id in rec.ids)[
                                0].unit,
                            'total_area': order.jobwork_barcode_lines.filtered(lambda pr: pr.product_id.id in rec.ids)[
                                0].total_area, 'product_id': rec.id}) for rec in order.jobwork_barcode_lines.product_id]
            rec.update({'finishing_work_id': order.id,
                        'inno_sizewise_rate_update_line': line})
        return rec

    def confirm_update(self):
        if self.finishing_work_id:
            for rec in self.inno_sizewise_rate_update_line:
                lines = self.finishing_work_id.jobwork_barcode_lines.filtered(lambda pr: pr.product_id.id in rec.product_id.ids)
                if lines:
                    if lines[0].rate != rec.rate:
                        old_rate = lines[0].rate
                        lines.write({'rate': rec.rate,'unit': rec.unit})
                        self.finishing_work_id.message_post(
                            body=f"<b>Updated Rate :</b><br/> <b> Old Rate {old_rate} New Rate {rec.rate} ₹</b> "
                                 f"for <b>product {rec.product_id.default_code}</b>")
                    if lines[0].total_area != rec.total_area:
                        old_area =lines[0].total_area
                        lines.write({'total_area': rec.total_area,'unit': rec.unit})
                        self.finishing_work_id.message_post(
                            body=f"<b>Updated Area :</b><br/> <b> Old Area {old_area} New Area {rec.total_area} </b> "
                                 f"for <b>product {rec.product_id.default_code}</b>")


class InnoUpdateRateSize_wize(models.TransientModel):
    _name = 'inno.sizewise.rate.update'

    size_id = fields.Many2one(comodel_name="inno.size", string="Size")
    rate = fields.Float(string="Rate", digits=(4, 2))
    inno_sample_rate_update_id = fields.Many2one('inno.sample.rate.update', )
    product_id = fields.Many2one(comodel_name="product.product", string="Product")
    total_area = fields.Float(string="Area", digits=(4, 4))
    unit = fields.Selection(
        [('sq_yard', 'Sq. Yard'), ('feet', 'Feet'), ('sq_feet', 'Sq. Feet'), ('choti', 'Choti'),
         ('sq_meter', 'Sq. Meter')],
        string='Units', tracking=True, store=True)
