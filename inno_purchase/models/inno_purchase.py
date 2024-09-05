import base64
from odoo import fields, models, _, api
from odoo.exceptions import UserError
from datetime import timedelta
from dateutil import relativedelta
from datetime import datetime


class InnoPurchase(models.Model):
    _name = "inno.purchase"
    _description = 'Purchase Job Work'
    _rec_name = "reference"
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'id DESC'

    READONLY_STATES = {
        'purchase': [('readonly', True)],
        'done': [('readonly', True)],
        'cancel': [('readonly', True)],
    }

    reference = fields.Char("Reference", default='/')
    subcontractor_id = fields.Many2one('res.partner', string='Vendor', tracking=True)
    issue_date = fields.Date(string='Date Issued', default=lambda *a: datetime.now(), )
    expected_received_date = fields.Date(string='Expected Date')
    total_day = fields.Integer(string='Total', compute='compute_total_days')
    inno_purchase_line = fields.One2many("inno.purchase.line", 'inno_purchase_id')
    state = fields.Selection(
        [('draft', 'DRAFT'), ('1_draft', 'DRAFT'), ('purchase', 'PURCHASE ORDER'), ('done', 'LOCKED'),
         ('cancel', 'CANCELLED')], string='Status', default='draft', tracking=True)
    types = fields.Selection(
        [('yarn', 'YARN'), ('wool', 'WOOL'), ('purchase', 'PURCHASE'),
         ('tufting_cloth_weaving', 'TUFTING CLOTH WEAVING'),
         ('newar_production', 'NEWAR PRODUCTION'), ('tana_job_order', 'TANA JOB ORDER'),
         ('third_backing_cloth', 'THIRD BACKING CLOTH'), ('spinning', 'SPINNING')],
        string='Type', )
    inno_receive_ids = fields.One2many("inno.receive", 'inno_purchase_id')
    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position',
                                         domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]")
    company_id = fields.Many2one('res.company', 'Company', required=True, index=True, states=READONLY_STATES,
                                 default=lambda self: self.env.company.id)
    currency_id = fields.Many2one('res.currency', 'Currency', required=True, states=READONLY_STATES,
                                  default=lambda self: self.env.company.currency_id.id)
    tax_totals = fields.Binary(compute='_compute_tax_totals', exportable=False)
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all')
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all',
                                     tracking=True)
    amount_total_words = fields.Char("Amount total in words", compute="_compute_amount_total_words")
    inno_receive_return_ids = fields.One2many("inno.receive", 'inno_purchase_return_id')
    picking_count = fields.Integer(compute='compute_delivery')
    planing_ids = fields.Many2many(comodel_name="inno.sale.order.planning", string="Plan NOs.")

    def upload_Planning_Product(self):
        if self.planing_ids:
            # self.order_line.unlink()
            record = self.planing_ids
            raw_material_group = ['acrlicy_yarn', 'polyster_yarn', 'jute_yarn', 'cotton_cone', 'silk', 'lefa', 'nylon',
                                  'woolen_yarn', 'cotton_yarn', 'yarn']
            products = record.sale_order_id.mrp_production_ids.move_raw_ids.product_id
            attribute_id = self.env['product.attribute'].search([('name', '=', 'SHADE')], limit=1)
            attribute_value = self.env['product.attribute.value'].search(
                [('attribute_id', '=', attribute_id.id), ('name', '=', 'NO Shade')], limit=1)
            for rec in products:
                if rec.product_tmpl_id.raw_material_group not in raw_material_group:
                    continue
                if rec.product_tmpl_id.with_shade:
                    self.update_or_create_po_line(rec)
                else:
                    sku = rec.product_tmpl_id.product_variant_ids.filtered(
                        lambda pv: attribute_value.name in pv.product_template_attribute_value_ids.mapped('name'))
                    if not sku:
                        rec.product_tmpl_id.attribute_line_ids.filtered(
                            lambda al: al.attribute_id.id == attribute_id.id).write(
                            {'value_ids': [(4, attribute_value.id)]})
                        sku = rec.product_tmpl_id.product_variant_ids.filtered(
                            lambda pv: attribute_value.name in pv.product_template_attribute_value_ids.mapped(
                                'name'))
                    if sku:
                        self.update_or_create_po_line(sku, rec,True)

    def update_or_create_po_line(self, product_id, actual_product=False, no_shade=False):
        record = self.planing_ids
        inno_purchase_line = self.inno_purchase_line.filtered(lambda pv: pv.product_id.id == product_id.id)
        if no_shade:
            qty = round(sum(record.sale_order_id.mrp_production_ids.move_raw_ids.filtered(
                lambda mv: mv.product_id.id == actual_product.id).mapped('product_uom_qty')), 3)
        else:
            qty = round(sum(record.sale_order_id.mrp_production_ids.move_raw_ids.filtered(
                lambda mv: mv.product_id.id == product_id.id).mapped('product_uom_qty')), 3)
        if inno_purchase_line:
            inno_purchase_line.write({'product_qty': inno_purchase_line.product_qty + qty})
        else:
            data = (0, 0, {'product_id': product_id.id,
                           # 'name': product_id.default_code if product_id.default_code else
                           # f"{product_id.name} {product_id.product_template_variant_value_ids.name}",
                           # 'price_unit': 10,
                           'product_qty': qty})
            self.write({'inno_purchase_line': [data]})

    def compute_delivery(self):
        for rec in self:
            cancel = self.env['inno.vendor.material'].search([('inno_purchase_id', '=', rec.id)]).__len__()
            rec.picking_count = cancel or 0

    def action_open_material_record(self):
        material_issue_id = self.env['inno.vendor.material'].search([('inno_purchase_id', '=', self.id)])
        action = {
            'name':  _("Material Issue"),
            'view_mode': 'form',
            'res_model': 'inno.vendor.material',
            'type': 'ir.actions.act_window',
        }
        if len(material_issue_id) > 1:
            action.update({'view_mode': 'tree,form', 'domain': [('id', 'in', material_issue_id.ids)]})
        else:
            action.update({'view_type': 'form', 'res_id': material_issue_id[0].id})
        return action



    @api.depends('amount_total', 'currency_id')
    def _compute_amount_total_words(self):
        for record in self:
            record.amount_total_words = record.currency_id.amount_to_text(record.amount_total)

    @api.depends('inno_purchase_line.price_total')
    def _amount_all(self):
        for order in self:
            order_lines = order.inno_purchase_line

            if order.company_id.tax_calculation_rounding_method == 'round_globally':
                tax_results = self.env['account.tax']._compute_taxes([
                    line._convert_to_tax_base_line_dict()
                    for line in order_lines
                ])
                totals = tax_results['totals']
                amount_untaxed = totals.get(order.currency_id, {}).get('amount_untaxed', 0.0)
                amount_tax = totals.get(order.currency_id, {}).get('amount_tax', 0.0)
            else:
                amount_untaxed = sum(order_lines.mapped('price_subtotal'))
                amount_tax = sum(order_lines.mapped('price_tax'))

            order.amount_untaxed = amount_untaxed
            order.amount_tax = amount_tax
            order.amount_total = order.amount_untaxed + order.amount_tax

    @api.depends('inno_purchase_line.tax_id', 'inno_purchase_line.price_subtotal', 'amount_total', 'amount_untaxed')
    def _compute_tax_totals(self):
        for order in self:
            order_lines = order.inno_purchase_line
            order.tax_totals = self.env['account.tax']._prepare_tax_totals(
                [x._convert_to_tax_base_line_dict() for x in order_lines],
                order.currency_id or order.company_id.currency_id,
            )

    @api.depends('issue_date', 'expected_received_date')
    def compute_total_days(self):
        for rec in self:
            rec.total_day = (rec.expected_received_date - rec.issue_date).days if \
                rec.issue_date and rec.expected_received_date else 0

    def button_confirm(self):
        if self._context.get('status') == 're_confirm':
            self.state = 'purchase'
        elif self._context.get('status') == 'cancel':
            self.state = 'cancel'
        elif self._context.get('status') == 'lock':
            self.state = 'done'
        else:
            self.state = '1_draft'
            if not self.inno_purchase_line:
                raise UserError(_("First you can add product and then confirm it"))
            for rec in self.inno_purchase_line:
                if rec.product_qty <= 0 and  rec.inno_purchase_id.types not in ['tufting_cloth_weaving','third_backing_cloth' ]:
                    raise UserError(_("Product quantity is always greater than zero"))
                if rec.rate <= 0:
                    raise UserError(_("Product rate is always greater than zero"))
            if self.reference == '/':
                if self.types == 'yarn':
                    self.write({'reference': self.env['ir.sequence'].next_by_code('po_inno_yarn_seq') or '/'})
                elif self.types == 'wool':
                    self.write({'reference': self.env['ir.sequence'].next_by_code('po_wool_seq') or '/'})
                elif self.types == 'purchase':
                    self.write({'reference': self.env['ir.sequence'].next_by_code('po_inno_pr_seq') or '/'})
                elif self.types == 'tufting_cloth_weaving':
                    self.write({'reference': self.env['ir.sequence'].next_by_code('po_inno_tcw_seq') or '/'})
                elif self.types == 'newar_production':
                    self.write({'reference': self.env['ir.sequence'].next_by_code('po_NP_seq') or '/'})
                elif self.types == 'tana_job_order':
                    self.write({'reference': self.env['ir.sequence'].next_by_code('po_inno_tjb_seq') or '/'})
                elif self.types == 'third_backing_cloth':
                    self.write({'reference': self.env['ir.sequence'].next_by_code('po_inno_tfc_seq') or '/'})
                elif self.types == 'spinning':
                    self.write({'reference': self.env['ir.sequence'].next_by_code('po_inno_spinning_seq') or '/'})
    def button_action_for_material_issue(self):
        pass

    def prepare_order_lines(self, lines):
        moves = []
        alloted_components = lines
        moves.extend([(0, 0, {'product_id': component.product_id.id,
                              'product_qty': component.product_qty,
                              'product_uom': component.uom_id.id,
                              'price_unit': component.rate,
                              }) for component in alloted_components])
        return moves

    def button_receive_products(self):
        if self.inno_receive_ids.filtered(lambda st: st.state in ['draft', 'ready']):
            raise UserError(_("First you will verify the previous received"))
        return {
            'name': 'Receive Products',
            'view_mode': 'form',
            'res_model': 'inno.receive.wizard',
            'type': 'ir.actions.act_window',
            'target': 'new',
            'context': "{'process': 'receive'}"
        }

    def open_purchase_order(self):
        record = self.env['purchase.order'].search([('inno_purchase_id', '=', self.id)])
        action = {
            'name': "Receipts",
            'view_mode': 'form',
            'res_model': 'purchase.order',
            'type': 'ir.actions.act_window',
        }
        if len(record) > 1:
            action.update({'view_mode': 'tree,form', 'domain': [('id', 'in', record.ids)]})
        else:
            action.update({'view_type': 'form', 'res_id': record[0].id})
        return action
