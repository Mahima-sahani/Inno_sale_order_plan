from odoo import fields, models,_


class AccountMove(models.Model):
    _inherit = 'account.move'

    job_work_id = fields.Many2one(comodel_name="main.jobwork")
    bazaar_id = fields.Many2one(comodel_name='main.baazar')
    division_ids = fields.Many2many("mrp.division", string='Division')


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    inno_area = fields.Char(string='Area')
    inno_price = fields.Float(string='Rate')


class AccountMoveLinePayment(models.Model):
    _inherit = 'account.payment'

    cheque = fields.Char(string='Cheque No')


class AccountPaymentRegisterTransient(models.TransientModel):
    _inherit = 'account.payment.register'

    cheque = fields.Char(string='Cheque No')

    def action_create_payments(self):
        payments = self._create_payments()
        payments.write({'cheque':self.cheque})

        if self._context.get('dont_redirect_to_payments'):
            return True

        action = {
            'name': _('Payments'),
            'type': 'ir.actions.act_window',
            'res_model': 'account.payment',
            'context': {'create': False},
        }
        if len(payments) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': payments.id,
            })
        else:
            action.update({
                'view_mode': 'tree,form',
                'domain': [('id', 'in', payments.ids)],
            })
        return action

