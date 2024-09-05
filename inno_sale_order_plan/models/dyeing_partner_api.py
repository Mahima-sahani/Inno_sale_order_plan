from odoo import api, fields, models


class DyeingPartnerApi(models.Model):
    _name = "dyeing.partner"
    _description = "DyeingPartner"

    _sql_constraints = [
        ('partner_uniq', 'unique (partner_id)', 'partner must be unique.')
    ]

    partner_id = fields.Many2one('res.partner', string='Partner Name', )
    api = fields.Char(string='API')
