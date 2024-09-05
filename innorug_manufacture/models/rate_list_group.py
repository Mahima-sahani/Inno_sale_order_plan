from odoo import models, fields


class RateListGroup(models.Model):
    _name = 'inno.product.rate.group'
    _description = 'Will maintain the rate list group'
    _rec_name = 'rate_list_group'

    rate_list_group = fields.Char(string='Rate List Group')
