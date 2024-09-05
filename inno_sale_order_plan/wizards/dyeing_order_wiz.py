from odoo import models, fields, api, _


class DyeingOrderWiz(models.TransientModel):
    _name = 'dyeing.order.wiz'

    def get_subcontractor_domain(self):
        dyeing_id = self.env['mrp.workcenter'].sudo().search([('name', '=', 'Dyeing')]).id
        if dyeing_id:
            query = f'select res_partner_id from res_partner_workcenter_rel where mrp_workcenter_id = {dyeing_id}'
            self._cr.execute(query)
            return [('id', 'in', [row[0] for row in self._cr.fetchall()])]
        else:
            return [('id', 'in', [])]

    partner_id = fields.Many2one(comodel_name='res.partner', string='Vendor Name', domain=get_subcontractor_domain)
    dyeing_order_wiz_line = fields.One2many(comodel_name='dyeing.order.wiz.line', inverse_name='dyeing_order_wiz_id')
    expected_date = fields.Date(string='Expected Date')

    @api.model
    def default_get(self, fields_list):
        rec = super().default_get(fields_list)
        dyeing_intend = self.env['dyeing.intend'].browse(self._context.get('active_ids'))
        if dyeing_intend:
            vals = [(0, 0, {'product_id': line.product_id.id, 'dyeing_intend_line': line.id,
                            'requested_qty': line.remaining_qty, 'po_no': line.dyeing_intend_id.order_no,
                            'qty_to_dye': int(line.remaining_qty)})
                    for line in dyeing_intend.sudo().dyeing_intend_line_ids if line.remaining_qty > 0]
            rec.update({'dyeing_order_wiz_line': vals})
        return rec

    def do_confirm(self):
        vals = []
        for rec in self.dyeing_order_wiz_line:
            if rec.qty_to_dye > 0:
                vals.append((0, 0, {'product_id': rec.product_id.id, 'quantity': rec.qty_to_dye,
                                    'uom_id': rec.product_id.uom_id.id, 'rate': rec.rate,
                                    'design_id': rec.dyeing_intend_line.dyeing_intend_id.product_tmpl_id.id,
                                    'dyeing_intend_line_no': rec.dyeing_intend_line.id,
                                    'po_no': rec.dyeing_intend_line.dyeing_intend_id.order_no}))
                rec.dyeing_intend_line.alloted_to_dyeing += rec.qty_to_dye
        if vals:
            order = self.env['dyeing.order'].create({
                'name': self.env['ir.sequence'].next_by_code('dyeing.order.seq'), 'issue_date': fields.date.today(),
                'partner_id': self.partner_id.id, 'dyeing_order_line_ids': vals,
                'expected_date': self.expected_date, 'state': 'draft',
                'division_id': self.dyeing_order_wiz_line.product_id.division_id.id})
            return {
                'type': 'ir.actions.act_window',
                'name': _("Dyeing Order"),
                'view_mode': 'form',
                'res_model': 'dyeing.order',
                'res_id': order.id
            }


class DyeingOrderWizLine(models.TransientModel):
    _name = 'dyeing.order.wiz.line'

    product_id = fields.Many2one(comodel_name='product.product', string='Product')
    dyeing_order_wiz_id = fields.Many2one(comodel_name='dyeing.order.wiz')
    dyeing_intend_line = fields.Many2one(comodel_name='dyeing.intend.line')
    requested_qty = fields.Float(digits=(12, 4), string='Required Qty')
    po_no = fields.Char()
    qty_to_dye = fields.Float(digits=(12, 4), string='Qty to Dyeing')
    rate = fields.Float(digits=(12, 4), string='Rate')
