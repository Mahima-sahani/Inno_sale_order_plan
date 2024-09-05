from odoo import models, fields, _, api
from odoo.exceptions import UserError


class FProductReceive(models.TransientModel):
    _name = 'ff.product.receive'

    jobwork_id = fields.Many2one(comodel_name='main.jobwork')
    product_receive_line = fields.One2many(comodel_name='ff.product.receive.line', inverse_name='product_receive_id')
    location_id = fields.Many2one(comodel_name='stock.location', string='Receive Location',
                                  domain=[('usage', '=', 'internal')])

    @api.model
    def default_get(self, fields_list):
        jobwork = self.env['main.jobwork'].browse(self._context.get('active_ids'))
        pickings = self.env['stock.picking'].search([('main_jobwork_id', '=', jobwork.id),
                                                     ('origin', '=', f"Main Job Work: {jobwork.reference}")])
        if pickings and not pickings.filtered(lambda pick: pick.state == 'done'):
            raise UserError(_("Material is not released Yet.\n"
                              "Please ask inventory manager to validate the delivery order."))
        res = super().default_get(fields_list)
        vals = [(0, 0, {'product_id': rec.product_id.id, 'jw_line_id': rec.id,
                        'qty_to_receive': rec.product_qty - (rec.received_qty + rec.return_quantity)})
                for rec in jobwork.jobwork_line_ids]
        res.update({'product_receive_line': vals, 'jobwork_id': jobwork.id})
        return res

    def do_confirm(self):
        invoice_lines = []
        journal_id = self.env['inno.config'].sudo().search([], limit=1).weaving_journal_id
        tax_id = self.jobwork_id.subcontractor_id.property_account_position_id.tax_ids.tax_dest_id
        all_barcodes = self.env['mrp.barcode']
        for rec in self.product_receive_line.filtered(lambda pl: pl.receive_qty > 0):
            jw = self.env['mrp.job.work'].browse(rec.jw_line_id)
            jw.received_qty = jw.received_qty+rec.receive_qty
            bcodes = jw.barcodes.filtered(lambda bcode: bcode.state == '3_allocated' and bcode.id not in self.jobwork_id.cancelled_barcodes.ids)
            if bcodes.__len__() >= rec.receive_qty:
                all_barcodes += bcodes[:rec.receive_qty]
            else:
                raise UserError(_("Barcode not availble."))
            invoice_lines.extend([
                (0, 0, {'product_id': rec.product_id.id, 'quantity': rec.receive_qty, 'price_unit': (jw.rate * jw.area),
                        'inno_area': f"{jw.area * rec.receive_qty}", 'inno_price': jw.rate,
                        'tax_ids': [(4, tax_id.id)] if tax_id else False,
                        'account_id': journal_id.default_account_id.id})])
        if invoice_lines:
            bill = self.env['account.move'].create({
                'move_type': 'in_invoice',
                'partner_id': self.jobwork_id.subcontractor_id.id,
                'date': fields.Datetime.now(),
                'invoice_date': fields.Datetime.now(),
                'job_work_id': self.jobwork_id.id,
                'invoice_line_ids': invoice_lines,
                'journal_id': journal_id.id
            })
        for rec in all_barcodes:
            rec.write({'state': '8_done', 'location_id': self.location_id.id})
            rec.move_barcode_inventory()


class FProductReceiveLine(models.TransientModel):
    _name = 'ff.product.receive.line'

    product_receive_id = fields.Many2one(comodel_name='ff.product.receive')
    product_id = fields.Many2one(comodel_name='product.product', string='Product')
    qty_to_receive = fields.Integer()
    receive_qty = fields.Integer()
    jw_line_id = fields.Integer()

    @api.onchange('receive_qty')
    def onchange_rec_qty(self):
        if self.receive_qty > self.qty_to_receive:
            raise UserError(_("Can't receive more quantity."))
        if self.receive_qty < 0:
            raise UserError(_("Can't enter Quantity less than zero."))
