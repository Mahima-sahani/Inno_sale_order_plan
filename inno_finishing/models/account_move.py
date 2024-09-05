from odoo import fields, models


class AccountMove(models.Model):
    _inherit = 'account.move'

    finishing_work_id = fields.Many2one(comodel_name="finishing.work.order")
    finishing_bazaar_id = fields.Many2one(comodel_name='finishing.baazar')


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    finishing_bazaar_id = fields.Many2one(comodel_name='finishing.baazar')
