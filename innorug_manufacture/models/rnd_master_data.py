from odoo import models, fields, api,_


class RndAttribute(models.Model):
    _name = 'rnd.master.data'
    _inherit = ['mail.thread', 'mail.activity.mixin']

    name = fields.Char()
    value_type = fields.Selection(selection=[('collection', 'Collection'), ('construction', 'Construction'),
                                             ('quality', 'Quality'), ('color_ways', 'Color ways'),
                                             ('style', 'Style'), ('color', 'Color'), ('pattern', 'Pattern'),
                                             ('contect', 'Contect'), ('face_content', 'Face Content')
                                             ])
    weight = fields.Float(string='Weight', digits=(12, 4))

    @api.model_create_multi
    def create(self, vals_list):
        if self._context.get('field_type'):
            vals_list[0].update({'value_type': self._context.get('field_type')})
        return super().create(vals_list)
