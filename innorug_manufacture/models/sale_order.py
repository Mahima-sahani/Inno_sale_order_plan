
from odoo import fields, models, _, api
from datetime import datetime
from odoo.exceptions import UserError

import logging
_logger = logging.getLogger(__name__)

class MrpSaleOrder(models.Model):
    _inherit = 'sale.order'

    main_job_work_ids = fields.Many2many("main.jobwork", string="Job Works")
    order_no = fields.Char("Order No")
    state = fields.Selection(
        [('draft', 'Draft'),
         ('sent', 'Review'),
         ('sale', 'Submit'),
         ('done', 'Done'),
         ('cancel', 'Cancelled')],
        string='Status', default='draft'
    )
    partner_id = fields.Many2one(
        'res.partner', string='Buyer', readonly=True,
        states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
        required=True, change_default=True, index=True, tracking=1,
        domain="[('type', '!=', 'private'), ('company_id', 'in', (False, company_id))]",)

    def action_confirm(self):
        for rec in self:
            if not rec.order_line:
                raise UserError(_("Sale Order Can't Be confirmed without Order Lines"))
        super().action_confirm()

    def name_get(self):
        return [(rec.id, f'{rec.name} [{rec.order_no}]') for rec in self]

    @api.model
    def _name_search(self, name='', args=None, operator='ilike', limit=100, name_get_uid=None):
        # Try to reverse the `name_get` structure
        if name:
            args = ['|', ['name', 'ilike', name], ['order_no', 'ilike', name]]
        else:
            return super()._name_search(name, args, operator, limit, name_get_uid)
        return self._search(args, limit=limit, access_rights_uid=name_get_uid)


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    pending_sale_order_qty = fields.Float(string='Pending Sale Qty')
    Total_sale_qty = fields.Float(string='Total Sale Qty')
    to_be_issue = fields.Boolean()
