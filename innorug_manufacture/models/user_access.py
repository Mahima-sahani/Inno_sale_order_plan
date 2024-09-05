from odoo import fields, models, api, _
from odoo.exceptions import UserError


class UserAccess(models.Model):
    _name = 'user.access'
    _description = "holds the records of the access given to the user."

    user_id = fields.Many2one(comodel_name="res.users", string="User")
    bazaar_receiving = fields.Boolean(string="Bazaar Receiving")
    bazaar_qa_verification = fields.Boolean(string="Bazaar QA Verification")

    @api.constrains('user_id')
    def check_unique_user(self):
        for record in self:
            if self.search_count([('user_id', '=', record.user_id.id)]) > 1:
                raise UserError(_('This user already have the access'))
