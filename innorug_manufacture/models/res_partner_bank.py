from odoo import models, fields


class ResPartnerBank(models.Model):
    _inherit = 'res.partner.bank'

    branch_name = fields.Char(string='Branch Name')
