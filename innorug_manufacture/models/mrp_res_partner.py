from odoo import fields, models, _,api


class Product(models.Model):
    _inherit = "res.partner"
    _description = "Res Partner"

    operation_ids = fields.Many2many(comodel_name='mrp.workcenter', relation='res_partner_workcenter_rel',
                                     string='Processes', help="Operations Contact can Do")
    is_loom_inspector = fields.Boolean(compute='compute_loom_inspector', store=True)
    is_buyer = fields.Boolean(string='Buyer')
    is_supplier = fields.Boolean(string='Supplier')
    is_jobworker = fields.Boolean(string='Job Worker')
    is_employee = fields.Boolean(string="Employee")
    pan_no = fields.Char(string="PAN Number")
    aadhar_no = fields.Char(string="Aadhar Number")
    is_far = fields.Boolean(string='Far?')
    incentive_penalities_ids = fields.One2many('inno.incentive.penalty', 'partner_id',
                                     string='Processes')
    job_worker_code = fields.Char("Code")
    is_pan_aadhar_link = fields.Boolean(string='Pan-Aadhar Link?')

    @api.depends('user_ids.groups_id')
    def compute_loom_inspector(self):
        group = self.env.ref('innorug_manufacture.group_inno_weaving_loom_inspector').id
        for rec in self:
            has_group = False
            if rec.user_ids:
                has_group = True if group in rec.user_ids[0].groups_id.ids else False
            rec.is_loom_inspector = has_group
