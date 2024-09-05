from odoo import models, fields


class MrpWorkCenters(models.Model):
    _inherit = 'mrp.workcenter'

    is_finishing_wc = fields.Boolean(string='Is Finishing work Center?')
    location_id = fields.Many2many(comodel_name='stock.location', string="Work Center Location")
    sequence_id = fields.Many2one(comodel_name='ir.sequence')

    def get_sequence(self):
        for rec in self:
            if not rec.sequence_id:
                sequence_available = self.env['ir.sequence'].search([('name', '=', f"{self.name}_{self.code}")])
                if sequence_available:
                    rec.sequence_id = sequence_available[0].id
                else:
                    name_split = self.name.split(' ')
                    if len(name_split) > 1:
                        prefix = ''.join([ch[0] for ch in name_split])
                    elif len(name_split) == 1:
                        prefix = ''.join(name_split[0][:2])
                    else:
                        prefix = ''
                    rec.sequence_id = self.env['ir.sequence'].create({'name': f"{self.name}_{self.code}",
                                                                      'prefix': f"{prefix.upper()}/JOB/", 'padding': 6})
