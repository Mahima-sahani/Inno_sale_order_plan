import base64
from odoo import fields, models, _, api

class InnoUsers(models.Model):
    _name = "inno.users"
    _description = 'Users Details'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _rec_name = "user_id"
    _inherits = {'res.users': 'user_id'}

    location_id = fields.Many2one(comodel_name='stock.location', string="Material Location Access", domain=[('usage', '=', 'internal')],tracking=True)
    division_id = fields.Many2one("mrp.division", string="Division Access")
    user_id = fields.Many2one("res.users", string="User")
    storage_location_ids = fields.Many2many(comodel_name='stock.location',
                                            string='Stores', domain=[('usage', '=', 'internal')])
    manager_id = fields.Many2one("res.users", string="Manager")

    @api.onchange('division_id','user_id','manager_id','location_id','storage_location_ids')
    def update_details_of_user(self):
        for rec in self:
            if rec.user_id:
                if rec.division_id:
                    rec.browse(self.id.origin).sudo().user_id.division_id = False
                    rec.browse(self.id.origin).sudo().user_id.write(
                        {'division_id': [(4, rec.division_id.id)]})
                if rec.location_id:
                    rec.browse(self.id.origin).sudo().user_id.write({'material_location_id' : rec.location_id.id})

    def create_inno_user_detais(self):
        res_users = self.env['res.users'].sudo().search([])
        for rec in res_users:
            inno_users = self.env['inno.users'].sudo().search([('user_id','=', rec.id)])
            if not inno_users:
                self.env['inno.users'].sudo().create({
                    'user_id': rec.id,
                })
class InnoLocation(models.Model):
    _inherit = "stock.location"

class InnoDivision(models.Model):
    _inherit = "mrp.division"







