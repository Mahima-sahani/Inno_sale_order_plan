from odoo import models, fields, api, _
from odoo.exceptions import UserError
from odoo.tools import float_is_zero, float_round


class UpdateSaleOrder(models.TransientModel):
    _name = 'update.sale.order.wiz'
    _description = 'Update Sale Order'

    def get_products_domain(self):
        products = self.env['inno.sale.order.planning'].browse(
            self._context.get('active_id')).sale_order_planning_lines.product_id
        domain = [('id', 'in', products.ids)]
        return domain

    planning_id = fields.Many2one(comodel_name='inno.sale.order.planning')
    order_wiz_lines = fields.One2many(comodel_name='update.sale.order.wiz.line', inverse_name='update_wiz_id')
    reasons = fields.Text("Reasons")
    barcodes = fields.Many2one(comodel_name='mrp.barcode')
    product_id = fields.Many2one("product.product", string="Product", domain=get_products_domain)
    is_new = fields.Boolean("NEW")
    order_wiz_new_lines = fields.One2many(comodel_name='update.sale.order.wiz.line', inverse_name='update_wiz_new_id')

    @api.onchange('product_id')
    def onchange_products(self):
        if self.product_id:
            if self.product_id.id not in self.order_wiz_lines.product_id.ids:
                line = [(0, 0, {'product_id': rec.product_id, 'manufacturing_qty': rec.manufacturing_qty,
                                'purchase_qty': rec.purchase_qty, 'rate': rec.rate, 'planning_line_id': rec.id, }) for
                        rec
                        in
                        self.planning_id.sale_order_planning_lines.filtered(
                            lambda sl: self.product_id.id in sl.product_id.ids) if rec]
                self.write({'order_wiz_lines': line, 'product_id': False})

    @api.onchange('barcodes')
    def onchange_barcodes(self):
        if self.barcodes:
            lines = self.order_wiz_lines.filtered(lambda ow: ow.product_id.id in self.barcodes.product_id.ids
                                                             and self.barcodes.sale_id.id in self.planning_id.sale_order_id.ids)
            lines.write({'barcodes': [(4, self.barcodes.id)]})
            lines.desc_manufacturing_qtys()
            self.barcodes = False

    @api.model
    def default_get(self, fields_list):
        rec = super().default_get(fields_list)
        planning_id = self.env['inno.sale.order.planning'].browse(self._context.get('active_id'))
        if planning_id:
            rec.update({'planning_id': planning_id.id, })
        return rec

    def do_confirm(self):
        new_planning_id = False
        if self.order_wiz_new_lines:
            lines = [(0, 0, {'product_id': rec.product_id.id,
                             'product_uom_qty': float(rec.manufacturing_qty),
                             'rate': float(rec.rate),
                             'buyer_up_code': rec.buyer_up_code,
                             'brand': rec.brand,
                             'planning_line_id': self.env['inno.sale.order.planning.line'].create({'product_id': rec.product_id.id,
                                                                                   'product_uom_qty': float(rec.manufacturing_qty),
                                                                                   'rate': float(rec.rate),
                                                                                   'is_new': True,
                                                                                    'sale_order_planning_id': self.planning_id.id,
                                                                                   'buyer_up_code': rec.buyer_up_code,
                                                                                   'brand': rec.brand,
                                                                                   'remaining_qty': float(rec.manufacturing_qty)}).id,
                             'remaining_qty': float(rec.manufacturing_qty)}) for rec in
                     self.order_wiz_new_lines if rec.product_id]
            if lines:
                new_planning_id = self.env['inno.sale.order.planning'].create({'customer_name': self.planning_id.customer_name.id,
                                       'order_date': self.planning_id.order_date,
                                       'due_date': self.planning_id.due_date,
                                       'order_no': f'RW{len(self.planning_id.amd_parent_line) + 1}/{self.planning_id.order_no}',
                                       'buyer_order_no': self.planning_id.buyer_order_no,
                                       'state': 'planning',
                                        'amd_parent_id' : self.planning_id.id,
                                       'sale_order_planning_lines': lines,
                                       'assigned_to': self.env.user.id})

        amd_lines = self.order_wiz_lines.filtered(lambda ol: ol.amended_qty > 0.00 and not ol.barcodes)
        rate_dsclines = self.order_wiz_lines.filtered(lambda ol: ol.id not in amd_lines.ids)
        if amd_lines:
            lines = [(0, 0, {'product_id': rec.product_id.id,
                             'product_uom_qty': float(rec.amended_qty),
                             'rate': float(rec.update_rate if rec.update_rate > 0.00 else rec.planning_line_id.rate),
                             'buyer_up_code': rec.planning_line_id.buyer_up_code,
                             'brand': rec.planning_line_id.brand,
                             'planning_line_id': rec.planning_line_id.id,
                             'remaining_qty': float(rec.amended_qty)}) for rec in
                     amd_lines if rec.product_id]
            if lines:
                if new_planning_id:
                    new_planning_id.write({"sale_order_planning_lines": lines})
                else:
                    amend_lines = [(0, 0, {'customer_name': self.planning_id.customer_name.id,
                                           'order_date': self.planning_id.order_date,
                                           'due_date': self.planning_id.due_date,
                                           'order_no': f'RW{len(self.planning_id.amd_parent_line) + 1}/{self.planning_id.order_no}',
                                           'buyer_order_no': self.planning_id.buyer_order_no,
                                           'state': 'planning',
                                           'sale_order_planning_lines': lines,
                                           'assigned_to': self.env.user.id
                                           })]
                    self.planning_id.write({'amd_parent_line': amend_lines})
            self.update_sale_order_rate(amd_lines)
        if rate_dsclines:
            dess_mrp = rate_dsclines.filtered(lambda ol: ol.desc_manufacturing_qty > 0.00)
            rate_lines = rate_dsclines.filtered(lambda ol: ol.id not in dess_mrp.ids and not ol.barcodes)
            if dess_mrp:
                for rec in dess_mrp:
                    production_id = self.planning_id.sale_order_id.mrp_production_ids.filtered(
                        lambda mrp: mrp.product_id.id in rec.product_id.ids)
                    if production_id.state == 'progress':
                        if rec.barcodes:
                            if production_id.product_qty == rec.barcodes.__len__():
                                production_id.action_cancel()
                            else:
                                for wo in production_id.workorder_ids:
                                    wo._compute_product_wo_qty()
                                self.change_prod_qty(rec, production_id)
                            rec.barcodes.write({'state': 'cancel'})
                            for rec in rec.barcodes:
                                rec.message_post(body=self.reasons, )
                        else:
                            raise UserError(
                                _(f'Please added the barcodes of {rec.product_id.default_code},  {production_id.name}'))
                    elif production_id.state == 'draft':
                        if float(production_id.product_qty) == rec.desc_manufacturing_qty:
                            production_id.write({'state': 'cancel'})
                            production_id.workorder_ids.write({'state': 'cancel'})
                        elif float(production_id.product_qty) > 0.00 and float(
                                production_id.product_qty) > rec.desc_manufacturing_qty:
                            production_id.action_confirm()
                            barcode = self.env['mrp.barcode'].search([('mrp_id', '=', production_id.id)])[
                                      :int(rec.desc_manufacturing_qty)]
                            self.change_prod_qty(rec, production_id)
                            barcode.write({'state': 'cancel'})
                            for rec in barcode:
                                rec.message_post(body=self.reasons, )
                self.update_sale_order_rate(dess_mrp)
            if rate_lines:
                self.update_sale_order_rate(rate_lines)

    @api.model
    def _update_finished_moves(self, production, new_qty, old_qty):
        """ Update finished product and its byproducts. This method only update
        the finished moves not done or cancel and just increase or decrease
        their quantity according the unit_ratio. It does not use the BoM, BoM
        modification during production would not be taken into consideration.
        """
        modification = {}
        push_moves = self.env['stock.move']
        for move in production.move_finished_ids:
            if move.state in ('done', 'cancel'):
                continue
            qty = (new_qty - old_qty) * move.unit_factor
            modification[move] = (move.product_uom_qty + qty, move.product_uom_qty)
            if self._need_quantity_propagation(move, qty):
                push_moves |= move.copy({'product_uom_qty': qty})
            else:
                move.write({'product_uom_qty': move.product_uom_qty + qty})

        if push_moves:
            push_moves._action_confirm()._action_assign()

        return modification

    @api.model
    def _need_quantity_propagation(self, move, qty):
        return move.move_dest_ids and not float_is_zero(qty, precision_rounding=move.product_uom.rounding)

    def change_prod_qty(self, rec, mo_id):
        precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        production = mo_id
        if len(rec.barcodes) > 0.00:
            product_qty = mo_id.product_qty - len(rec.barcodes)
        else:
            product_qty = mo_id.product_qty - rec.desc_manufacturing_qty
        produced = sum(production.move_finished_ids.filtered(lambda m: m.product_id == production.product_id).mapped(
            'quantity_done'))
        if product_qty < produced:
            format_qty = '%.{precision}f'.format(precision=precision)
            raise UserError(_(
                "You have already processed %(quantity)s. Please input a quantity higher than %(minimum)s ",
                quantity=format_qty % produced,
                minimum=format_qty % produced
            ))
        old_production_qty = production.product_qty
        new_production_qty = product_qty
        done_moves = production.move_finished_ids.filtered(
            lambda x: x.state == 'done' and x.product_id == production.product_id)
        qty_produced = production.product_id.uom_id._compute_quantity(sum(done_moves.mapped('product_qty')),
                                                                      production.product_uom_id)

        factor = (new_production_qty - qty_produced) / (old_production_qty - qty_produced)
        update_info = production._update_raw_moves(factor)
        documents = {}
        for move, old_qty, new_qty in update_info:
            iterate_key = production._get_document_iterate_key(move)
            if iterate_key:
                document = self.env['stock.picking']._log_activity_get_documents({move: (new_qty, old_qty)},
                                                                                 iterate_key, 'UP')
                for key, value in document.items():
                    if documents.get(key):
                        documents[key] += [value]
                    else:
                        documents[key] = [value]
        production._log_manufacture_exception(documents)
        self._update_finished_moves(production, new_production_qty - qty_produced, old_production_qty - qty_produced)
        production.write({'product_qty': new_production_qty})

        for wo in production.workorder_ids:
            operation = wo.operation_id
            wo.duration_expected = wo._get_duration_expected(ratio=new_production_qty / old_production_qty)
            quantity = wo.qty_production - wo.qty_produced
            if production.product_id.tracking == 'serial':
                quantity = 1.0 if not float_is_zero(quantity, precision_digits=precision) else 0.0
            else:
                quantity = quantity if (quantity > 0 and not float_is_zero(quantity, precision_digits=precision)) else 0
            wo._update_qty_producing(quantity)
            if wo.qty_produced < wo.qty_production and wo.state == 'done':
                wo.state = 'progress'
            if wo.qty_produced == wo.qty_production and wo.state == 'progress':
                wo.state = 'done'
            # assign moves; last operation receive all unassigned moves
            # TODO: following could be put in a function as it is similar as code in _workorders_create
            # TODO: only needed when creating new moves
            moves_raw = production.move_raw_ids.filtered(
                lambda move: move.operation_id == operation and move.state not in ('done', 'cancel'))
            if wo == production.workorder_ids[-1]:
                moves_raw |= production.move_raw_ids.filtered(lambda move: not move.operation_id)
            moves_finished = production.move_finished_ids.filtered(
                lambda move: move.operation_id == operation)  # TODO: code does nothing, unless maybe by_products?
            moves_raw.mapped('move_line_ids').write({'workorder_id': wo.id})
            (moves_finished + moves_raw).write({'workorder_id': wo.id})

        mo_id.filtered(lambda mo: mo.state in ['confirmed', 'progress']).move_raw_ids._trigger_scheduler()

        return {}

    def update_sale_order_rate(self, lines):
        for rec in lines:
            if rec.amended_qty > 0.00 or rec.update_rate > 0.00 or rec.desc_manufacturing_qty > 0.00:
                lines = [(0, 0, {'desc_manufacturing_qty': rec.desc_manufacturing_qty,
                                 'amended_qty': rec.amended_qty,
                                 'update_rate': rec.update_rate,
                                 'reasons': self.reasons,
                                 'barcodes': [(4, line.id) for line in
                                              rec.barcodes] if rec.desc_manufacturing_qty > 0.00 and rec.barcodes else False,
                                 })]
                rec.planning_line_id.write({'revised_lines': lines})
            if rec.update_rate > 0.00:
                self.planning_id.sale_order_id.order_line.filtered(
                    lambda ol: rec.product_id.id in ol.product_id.ids).write({'price_unit': rec.update_rate})
                if self.planning_id.amd_parent_line:
                    for line in self.planning_id.amd_parent_line:
                        line.sale_order_planning_lines.filtered(
                            lambda pl: rec.product_id.id in pl.product_id.ids).write({'rate': rec.update_rate})
                        if line.sale_order_id:
                            line.sale_order_id.order_line.filtered(
                                lambda ol: rec.product_id.id in ol.product_id.ids).write(
                                {'price_unit': rec.update_rate})


class UpdateSaleOrderLine(models.TransientModel):
    _name = 'update.sale.order.wiz.line'

    update_wiz_id = fields.Many2one(comodel_name='update.sale.order.wiz')
    product_id = fields.Many2one("product.product", string="Product", domain=[('is_raw_material', '=', False)])
    onloom_qty = fields.Float("Onloom Qty")
    manufacturing_qty = fields.Float("Manufacturing Qty")
    purchase_qty = fields.Float("Purchase Qty")
    desc_manufacturing_qty = fields.Float("Desc MRP Qty")
    amended_qty = fields.Float("AMD MRP Qty")
    rate = fields.Float("Rate")
    update_rate = fields.Float("Update Rate")
    planning_line_id = fields.Many2one("inno.sale.order.planning.line", )
    barcodes = fields.Many2many(comodel_name='mrp.barcode')
    update_wiz_new_id = fields.Many2one(comodel_name='update.sale.order.wiz')
    # new_product_id = fields.Many2one("product.product", string="New SkU", domain=[('is_raw_material', '=', False)])
    buyer_up_code = fields.Char("BuyerUpcCode")
    brand = fields.Char("Brand")

    @api.onchange('desc_manufacturing_qty')
    def onchange_add_barcodes(self):
        if self.product_id and self.desc_manufacturing_qty > 0.00:
            barcode = self.env['mrp.barcode'].search([('mrp_id', '=', self.update_wiz_id.planning_id.sale_order_id.mrp_production_ids.filtered(
                lambda mrp: mrp.product_id.id in self.product_id.ids).id),('state', '=', '1_draft')])[:int(self.desc_manufacturing_qty)]
            if barcode.__len__() == int(self.desc_manufacturing_qty) :
                self.write({'barcodes': [(4, rec.id)for rec in barcode]})
            else:
                raise UserError(_(f'Barcodes {barcode.__len__()}, Less Qty {self.desc_manufacturing_qty}'))

    def desc_manufacturing_qtys(self):
        for rec in self:
            rec.desc_manufacturing_qty = self.barcodes.__len__()
