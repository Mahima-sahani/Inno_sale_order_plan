from odoo import models, fields, _, api
from odoo.exceptions import UserError


class InnoAmendQuantity(models.TransientModel):
    _name = 'inno.amend.return'
    _description = 'Will allow user to amend Quantity for job works'

    job_order_id = fields.Many2one(comodel_name='main.jobwork')
    amend_return_ids = fields.One2many(comodel_name='inno.amend.return.line', inverse_name='amend_return_id')

    @api.model
    def default_get(self, fields_list):
        rec = super().default_get(fields_list)
        job_order = self.env['main.jobwork'].browse(self._context.get('active_id'))
        if job_order.main_jobwork_components_lines:
            vals = [(0, 0, {'product_id': line.product_id.id, 'product_uom': line.product_uom.id,
                            'component_line_id': line.id}) for line in job_order.main_jobwork_components_lines]
            rec.update({'job_order_id': job_order.id, 'amend_return_ids': vals})
        return rec

    def button_confirm(self):
        self.transfer_stock_to_subcontracter()
        if self._context.get('process') == 'amend':
            for rec in self.amend_return_ids:
                rec.component_line_id.amended_quantity = rec.component_line_id.amended_quantity + rec.quantity
        elif self._context.get('process') == 'return':
            for rec in self.amend_return_ids:
                rec.component_line_id.returned_quantity = rec.component_line_id.returned_quantity + rec.quantity

    def transfer_stock_to_subcontracter(self):
        operation_type, source_location, destination_location = self.get_location_and_opoeration()
        try:
            job_stock_move = self.prepare_job_stock_move(source_location, destination_location)
            vals = {
                'name': operation_type.sequence_id.next_by_id(),
                'partner_id': self.job_order_id.subcontractor_id.id,
                'picking_type_id': operation_type.id,
                'location_id': source_location,
                'location_dest_id': destination_location,
                'move_ids': job_stock_move,
                'state': 'draft',
                'main_jobwork_id': self.job_order_id.id
            }
            if self._context.get('process') == 'amend':
                vals.update({'origin': f"Main Job Work: {self.job_order_id.reference}"})
            elif self._context.get('process') == 'return':
                vals.update({'origin': f"Return/Main Job Work: {self.job_order_id.reference}"})
            return self.env['stock.picking'].sudo().create(vals)
        except Exception as ex:
            raise UserError(_(ex))

    def get_location_and_opoeration(self):
        if not self.env.user.material_location_id:
            raise UserError(_("Please Ask Your Admin to set your Material Location."))
        warehouse = self.env.user.material_location_id.warehouse_id
        operation_type = warehouse.out_type_id
        source_location = self.env.user.material_location_id.id
        dest_location = self.env['stock.location'].search([('usage', '=', 'supplier')], limit=1).id
        if self._context.get('process') == 'amend':
            return operation_type, source_location, dest_location
        elif self._context.get('process') == 'return':
            return operation_type.return_picking_type_id, dest_location, source_location

    def prepare_job_stock_move(self, source_location, destination_location):
        """
        Prepare the stock move line as per the component set in the selected operation
        """
        moves = [(0, 0, {'name': f"Transfer : {self.job_order_id.reference}", 'product_id': component.product_id.id,
                         'product_uom_qty': component.quantity, 'product_uom': component.product_uom.id,
                         'location_id': source_location, 'location_dest_id': destination_location})
                 for component in self.amend_return_ids if component.quantity > 0]
        return moves


class InnoAmendQuantityLine(models.TransientModel):
    _name = 'inno.amend.return.line'
    _description = 'Line records for amend quanty model'

    product_id = fields.Many2one(comodel_name="product.product", string="Product", readonly="1")
    quantity = fields.Float(string="Quantity")
    product_uom = fields.Many2one(comodel_name="uom.uom", string="UOM")
    amend_return_id = fields.Many2one(comodel_name="inno.amend.return")
    component_line_id = fields.Many2one(comodel_name='subcontractor.alloted.product')
