from odoo import models, fields


class InnoConfig(models.Model):
    _name = 'inno.config'
    _description = 'Holds the the configurations of all the inherited models'

    name = fields.Char(string='Name', default='Inno Configuration Data')
