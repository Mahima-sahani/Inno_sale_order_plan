from odoo import models, fields, api, _


class InnoProductWorkCenter(models.Model):
    _name = 'inno.product.workcenter.relation'
    _description = 'will connect product with work centers'

    product_id = fields.Many2one(comodel_name='product.template', string='Design')
    work_center_id = fields.Many2one(comodel_name='mrp.workcenter')
    price_list_id = fields.Many2one(comodel_name='inno.rate.list')
    uom_id = fields.Many2one(comodel_name='uom.uom', string="Unit of Measure")
    actual_product_id = fields.Many2one(comodel_name='product.product', string='SKU')
    is_outside = fields.Boolean(string='Outside')
    is_far = fields.Boolean(string='Far')
    rate_group_id = fields.Many2one(comodel_name='inno.product.rate.group', string='RateList Group')
    fixed_incentive = fields.Float(string="Fixed Incentive", digits=(3,3))
    expire_incentive = fields.Float(string="Expirable Incentive", digits=(3, 3))


class InnoRateList(models.Model):
    _name = 'inno.rate.list'
    _description = 'Manage Rate List'

    name = fields.Char()
    base_price = fields.Float(string="Base Price", digits='Product Price')
    variable_price = fields.Float(digits='Product Price')
    condition_required = fields.Boolean(string="Conditional")
    product_field_id = fields.Many2one(comodel_name='ir.model.fields', domain=[('model', 'in', ['product.template', 'product.product', 'inno.product.rate.group'])])
    price_condition_ids = fields.One2many(comodel_name='inno.price.condition', inverse_name='price_list_id')
    field_type = fields.Char()
    loss = fields.Float(string='Loss', digits=(12, 4))

    @api.onchange('operation_id')
    def onchange_user_vendors_id(self):
        if self.operation_id:
            domain = [
                ('id', 'in', self.env['res.partner'].search([]).filtered(
                    lambda pt: self.operation_id.id in pt.operation_ids.ids).ids)]
            return {'domain': {'subcontractor_id': domain}}
        else:
            return {'domain': {'subcontractor_id': []}}

    @api.onchange('product_field_id')
    def _compute_field_type(self):
        for rec in self:
            rec.price_condition_ids.unlink()
            rec.write({'field_type': rec.product_field_id.ttype if rec.product_field_id.ttype in ['selection', 'float'] else 'other'})


class InnoPriceConditions(models.Model):
    _name = 'inno.price.condition'
    _description = 'Holds the condition related to price'

    condition = fields.Selection(selection=[('>', '>'), ('<', '<'), ('=', '=')])
    product_field_id = fields.Many2one(related='price_list_id.product_field_id')
    matching_value = fields.Float()
    matching_selection = fields.Many2one(comodel_name='ir.model.fields.selection')
    matching_data = fields.Char()
    base_price = fields.Float(string="Base Price", digits='Product Price')
    variable_price = fields.Float(digits='Product Price')
    price_list_id = fields.Many2one(comodel_name='inno.rate.list')
    display_value = fields.Char(string='Value', compute='_compute_value', store=True)

    @api.depends('matching_value', 'matching_selection', 'matching_data')
    def _compute_value(self):
        for rec in self:
            rec.display_value = rec.matching_value or rec.matching_selection.name or rec.matching_data or False

    @api.onchange('product_field_id')
    def onchange_product_id(self):
        if self.product_field_id.ttype not in ['float']:
            self.condition = '='
        if self.product_field_id:
            return {'domain': {'matching_selection': [('field_id', '=', self.product_field_id.id)]}}
