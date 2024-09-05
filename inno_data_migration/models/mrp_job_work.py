from odoo import fields, models


class PurchaseJobWork(models.Model):
    _inherit = 'mrp.job.work'

    sale_order_number = fields.Char()