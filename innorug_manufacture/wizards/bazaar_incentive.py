from odoo import models, fields, api, _


class InnoIncentive(models.TransientModel):
    _name = 'inno.incentive'
    _description = 'incentive to particular barcode'

    barcode_id = fields.Many2one(comodel_name='mrp.barcode', string='Barcode')
    product_id = fields.Many2one(comodel_name='product.product', string='Product')
    bazaar_id = fields.Many2one(comodel_name='main.baazar', string='Bazaar')
    bazaar_line_id = fields.Many2one(comodel_name='mrp.baazar.product.lines')
    area = fields.Float(related='bazaar_line_id.job_work_id.area')
    amount = fields.Float()
    uom_id = fields.Many2one(comodel_name='uom.uom')
    incentive_added = fields.Boolean()
    remark = fields.Char()

    def add_incentive(self):
        self.env['inno.incentive.penalty'].create({
            'barcode_id': self.barcode_id.id,
            'remark': self.remark,
            'record_date': fields.Datetime.now(),
            'amount': self.amount * self.area,
            'model_id': self.env.ref('innorug_manufacture.model_main_jobwork').id,
            'workcenter_id': self.barcode_id.current_process.id,
            'rec_id': self.bazaar_id.main_jobwork_id.id,
            'type': 'incentive'
        })
        self.incentive_added = True
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'tree',
            'res_model': 'inno.incentive',
            'target': 'new',
            'res_id': self.id,
            'domain': [('incentive_added', '=', False), ('bazaar_id', '=', self.bazaar_id.id)]
        }
