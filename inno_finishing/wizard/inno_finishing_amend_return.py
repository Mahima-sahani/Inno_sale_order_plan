from odoo import fields, models, api, _
from odoo.exceptions import UserError


class FinishingAmendReturn(models.TransientModel):
    _name = 'finishing.amendreturn.wiz'
    _description = 'Will allow user to amend Quantity for job works'

    job_order_id = fields.Many2one(comodel_name='finishing.work.order')
    amend_return_ids = fields.One2many(comodel_name='finishing.amendreturn.wiz.line', inverse_name='amend_return_id')
    area = fields.Float("Area/Choti")
    status = fields.Selection([('yes', 'YES'),
                               ('no', 'NO')],
                              string='Hishabh', tracking=True)
    is_hishabh = fields.Boolean(string='Hishabh', tracking=True)
    is_external = fields.Boolean(related="job_order_id.is_external")

    @api.model
    def default_get(self, fields_list):
        rec = super().default_get(fields_list)
        job_order = self.env['finishing.work.order'].browse(self._context.get('active_id'))
        if self._context.get('process') == 'hishabh':
            vals = [(0, 0, {'product_id': line.product_id.id, 'product_uom': line.uom_id.id,
                            'qty_released': line.qty_released, 'qty_amended': line.qty_amended,
                            'qty_return': line.qty_return,
                            'extra': line.extra, 'qty_retained': line.qty_retained, 'qty_previous': line.qty_previous,
                            'rate': line.rate, 'closed': line.closed,
                            'component_line_id': line.id}) for line in
                    job_order.material_lines.filtered(lambda ar: not ar.added_in_bill)]
            rec.update({'job_order_id': job_order.id, 'is_hishabh': True, 'amend_return_ids': vals})
        else:
            if job_order.material_lines:
                vals = [(0, 0, {'product_id': line.product_id.id, 'product_uom': line.uom_id.id,
                                'location_id': line.location_id.id,
                                'component_line_id': line.id}) for line in job_order.material_lines]
                rec.update({'job_order_id': job_order.id, 'amend_return_ids': vals})
        return rec

    def button_confirm(self):
        if self._context.get('process') == 'amend':
            self.transfer_stock_to_subcontracter()
        elif self._context.get('process') == 'return':
            self.transfer_stock_to_subcontracter()
        elif self._context.get('process') == 'hishabh':
            if self.status == 'yes':
                pending_material_id = self.env['inno.pending.material'].sudo().search(
                    [('subcontractor_id', '=', self.job_order_id.subcontractor_id.id),
                     ('process', '=', 'finishing')], limit=1)
                not_closed_ids = self.amend_return_ids.filtered(lambda ar: not ar.closed)
                if not_closed_ids:
                    raise UserError("First you can closed material hishabh")
                for rec in self.amend_return_ids:
                    if rec.qty_retained > 0.0 and rec.closed:
                        if not pending_material_id:
                            pending_material_id = self.env['inno.pending.material'].sudo().create(
                                {'subcontractor_id': self.job_order_id.subcontractor_id.id, 'process':
                                    'finishing'})
                        if pending_material_id:
                            material_lines = pending_material_id.material_line_ids.filtered(
                                lambda pr: rec.product_id.id in pr.product_id.ids)
                            if material_lines:
                                material_lines.quantity += rec.qty_retained
                                rec.component_line_id.qty_retained += rec.qty_retained
                                rec.component_line_id.rate = rec.rate

                            else:
                                pending_material_id.write({'material_line_ids': [
                                    (0, 0, {'product_id': rec.product_id.id, 'quantity': rec.qty_retained})]})
                                rec.component_line_id.qty_retained += rec.qty_retained
                                rec.component_line_id.rate = rec.rate
                    rec.component_line_id.closed = True
            else:
                raise UserError("First you can select Hishabh Type")

    def transfer_stock_to_subcontracter(self):
        if self.amend_return_ids:
            for rec in self.amend_return_ids.location_id:
                lines = self.amend_return_ids.filtered(lambda id: id.location_id.id == rec.id)
                dest_location = self.env['stock.location'].search([('usage', '=', 'supplier')], limit=1)
                operation_type, source_location, destination_location = self.get_location_and_opoeration(rec,
                                                                                                         dest_location,
                                                                                                         lines)
                try:
                    job_stock_move = self.prepare_job_stock_move(source_location, destination_location, lines)
                    vals = {
                        'name': operation_type.sequence_id.next_by_id(),
                        'partner_id': self.job_order_id.subcontractor_id.id,
                        'picking_type_id': operation_type.id,
                        'location_id': source_location,
                        'location_dest_id': destination_location,
                        'move_ids': job_stock_move,
                        'state': 'draft',
                        'finishing_work_id': self.job_order_id.id
                    }
                    if self._context.get('process') == 'amend':
                        vals.update(
                            {'origin': f"Main Job Work: {self.job_order_id.name}", 'extra_material_type': 'amended'})
                    elif self._context.get('process') == 'return':
                        vals.update({'origin': f"Return/Main Job Work: {self.job_order_id.name}",
                                     'extra_material_type': 'return'})
                    return self.env['stock.picking'].sudo().create(vals)
                except Exception as ex:
                    raise UserError(_(ex))

    def get_location_and_opoeration(self, rec, dest, lines):
        warehouse = rec.warehouse_id
        operation_type = warehouse.out_type_id
        source_location = rec.id
        if self._context.get('process') == 'amend':
            return operation_type, source_location, dest.id
        elif self._context.get('process') == 'return':
            return operation_type.return_picking_type_id, dest.id, source_location

    def prepare_job_stock_move(self, source_location, destination_location, lines):
        """
        Prepare the stock move line as per the component set in the selected operation
        """
        moves = [(0, 0, {'name': f"Transfer : {self.job_order_id.name}", 'product_id': component.product_id.id,
                         'product_uom_qty': component.quantity, 'product_uom': component.product_uom.id,
                         'location_id': source_location, 'location_dest_id': destination_location})
                 for component in lines if component.quantity > 0]
        return moves


class FinishingAmendQuantityLine(models.TransientModel):
    _name = 'finishing.amendreturn.wiz.line'
    _description = 'Line records for amend quanty model'

    product_id = fields.Many2one(comodel_name="product.product", string="Product", readonly="1")
    quantity = fields.Float(string="Quantity")
    product_uom = fields.Many2one(comodel_name="uom.uom", string="UOM")
    amend_return_id = fields.Many2one(comodel_name="finishing.amendreturn.wiz")
    component_line_id = fields.Many2one(comodel_name='finishing.materials')
    location_id = fields.Many2one("stock.location", string="Location",
                                  default=lambda self: self.env.user.material_location_id.id,
                                  domain=[('usage', '=', 'internal')])
    qty_released = fields.Float("Released", related="material_id.qty_released", digits=(12, 4))
    qty_amended = fields.Float("Amended", related="material_id.qty_amended", digits=(12, 4))
    qty_return = fields.Float("Return", related="material_id.qty_return", digits=(12, 4))
    extra = fields.Boolean("If Extra", related="material_id.extra")
    qty_retained = fields.Float("Retained", digits=(12, 4))
    material_id = fields.Many2one("finishing.materials")
    rate = fields.Float(string="Rate", digits=(4, 2))
    price_subtotal = fields.Monetary(compute='_compute_amount', string='Subtotal', store=True)
    currency_id = fields.Many2one(related='amend_return_id.job_order_id.currency_id', store=True, string='Currency',
                                  readonly=True)
    closed = fields.Boolean("Closed")
    remark = fields.Text("Remarks")
    qty_previous = fields.Float("Previous", related="material_id.qty_previous", digits=(12, 4))

    @api.depends('qty_released', 'qty_amended', 'qty_return', 'extra', 'qty_retained', 'rate', 'price_subtotal')
    def _compute_amount(self):
        for rec in self:
            rec.price_subtotal = 0.0
            rec.write({'price_subtotal': rec.rate * (
                    rec.qty_amended - rec.qty_return - rec.qty_retained) if rec.extra else rec.rate * (
                    rec.qty_released - rec.qty_return)})
