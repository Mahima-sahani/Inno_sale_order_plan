from odoo import models, fields, _, api
from odoo.exceptions import UserError, ValidationError, MissingError


class Orders(models.TransientModel):
    _name = 'order.wizards'
    _description = 'Create Order for purchase order and manufacturing order'

    product_temp_id = fields.Many2one(comodel_name ="product.template", string ="Design Name" )
    issue_date = fields.Datetime(default=fields.Datetime.now)
    expected_date = fields.Datetime()
    partner_id = fields.Many2one(comodel_name="res.partner", string="Vendor")
    order_wizards_lines = fields.One2many(comodel_name="order.wizards.line", inverse_name="order_wizards_id")
    is_purchase = fields.Boolean("Purchase")
    is_delivery = fields.Boolean("delivary")
    research_id = fields.Many2one(comodel_name="inno.research", string="Research")
    # carrier_id = fields.Many2one(comodel_name ="delivery.carrier", string="Carrier")


    @api.model
    def default_get(self, fields_list):
        rec = super().default_get(fields_list)
        inno_id = self.env['inno.research'].browse(self._context.get('active_id'))
        rec.update({'research_id': inno_id.id, 'product_temp_id' : inno_id.product_tmpl_id.id})
        if self._context.get('type') == 'mrp_order':
            vals = [(0, 0, {'product_id': line.product_id.id, }) for line in inno_id.research_lines]
            rec.update({'order_wizards_lines': vals})
        return rec

    def do_manufacturing(self):
        qty = False
        for order in self:
            qty = order.check_product_qty(order.order_wizards_lines)
            if qty:
                for rec in order.order_wizards_lines:
                    if rec.product_qty:
                        mrp_id = self.env["mrp.production"].sudo().create({
                                "product_id" : rec.product_id.id,
                                "product_qty" : rec.product_qty,
                                "date_planned_start" : self.issue_date,
                                "research_id" : self.research_id.id,
                                "is_sample": True
                            })
                        print(mrp_id)
                self.research_id._get_count()
                self.research_id.state = "3_product_sampling"
                self.research_id.is_active_verify = True

    def check_product_qty(self, lines):
        for rec in lines:
            if rec.product_qty <= 0:
                raise UserError("Add Product qty")
        return True


    def do_purchase(self):
        qty = False
        for rec in self:
            qty = rec.check_product_qty(rec.order_wizards_lines)
            if qty:
                if not rec.partner_id:
                    raise UserError("Please Salect Vendor")
                if rec.partner_id:
                    purchase_id = self.env["purchase.order"].create({
                        "partner_id" : rec.partner_id.id,
                        "date_order" : rec.issue_date,
                        "date_planned" : rec.expected_date,
                        "research_id" : rec.research_id.id,
                    })
                    if purchase_id:
                        for line in rec.order_wizards_lines :
                            purchase_line =self.env["purchase.order.line"].create({
                            "product_id" : line.product_id.id,
                            "product_qty" : line.product_qty,
                            "order_id" : purchase_id.id
                        })
                            if purchase_line :
                                purchase_id.order_line += purchase_line
                    rec.research_id.purchase_id = purchase_id.id
                    rec.research_id.state = "3_product_sampling"

    def do_shipment(self):
        warehouse = self.env['inno.config'].sudo().search([], limit=1).main_warehouse_id
        if not warehouse:
            raise UserError(_("Please configure a default warehouse."))
        operation_type = warehouse.out_type_id
        source_location = self.env['stock.location'].search([('usage', '=', 'production')], limit=1).id
        dest_location = self.env['stock.location'].search([('usage', '=', 'supplier')], limit=1).id
        # operation_type = self.env['stock.picking.type'].search([('sequence_code', '=', 'RES'),
        #                                                         ('code', '=', 'outgoing'),
        #                                                         ('warehouse_id', '=', warehouse.id)])
        try:
            job_stock_move = self.prepare_job_stock_move(operation_type)
            pick_id=self.env['stock.picking'].create({
                'name': operation_type.sequence_id.next_by_id(),
                'partner_id': self.partner_id.id,
                'picking_type_id': operation_type.id,
                'location_id': operation_type.default_location_src_id.id,
                'location_dest_id': dest_location,
                'move_ids': job_stock_move,
                'state': 'draft',
                # 'carrier_id' : self.carrier_id.id,
                'research_id': self.research_id.id,
            })
            self.research_id.pick_id = pick_id
            self.research_id.state = "4_shipment"
        except Exception as ex:
            raise UserError(_(ex))

    def prepare_job_stock_move(self, operation_type):
        """
        Prepare the stock move line as per the component set in the selected operation
        """
        dest_location = self.env['stock.location'].search([('usage', '=', 'supplier')], limit=1).id
        moves = []
        alloted_components = self.order_wizards_lines
        moves.extend([(0, 0, {'name': f"Test",
                              'product_id': component.product_id.id,
                              'product_uom_qty': component.allote_qty,
                              # 'product_uom': component.product_uom.id,
                              'location_id': operation_type.default_location_src_id.id,
                              'location_dest_id': dest_location
                              }) for component in alloted_components])
        return moves

    def do_cancel(self):
        pass


class OrderLines(models.TransientModel):
    _name = "order.wizards.line"
    _description = "Create Order wizads lines"

    product_id = fields.Many2one(comodel_name="product.product", string="Product")
    available_qty = fields.Float("On-Hand Qty", related="product_id.qty_available")
    product_qty = fields.Integer("Quantity(Units)")
    allote_qty = fields.Integer("Allote Qty(Units)")
    order_wizards_id = fields.Many2one(comodel_name="order.wizards", string="Order")

    @api.onchange('allote_qty')
    def onchange_quantity(self):
        for rec in self:
            if rec.allote_qty > rec.available_qty :
                raise UserError(_("Can't allocate more quantities than available in warehouse."))

