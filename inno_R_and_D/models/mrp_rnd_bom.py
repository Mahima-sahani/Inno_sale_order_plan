from odoo import models, fields, api,_
from odoo.exceptions import UserError


class MrpBom(models.Model):
    _inherit = "mrp.bom"

    research_id = fields.Many2one(comodel_name="inno.research", string="Research")


    def button_add_bom_percent(self):
        return {
            'type': 'ir.actions.act_window',
            'name': "Percentage",
            'view_mode': 'form',
            'res_model': 'bom.percent.wizard',
            'target': 'new'
        }


class MrpBomLines(models.Model):
    _inherit = "mrp.bom.line"

    research_id = fields.Many2one(comodel_name="inno.research", string="Research")
    rnd_bom_id = fields.Many2one(related="research_id.bom_id", string="Bom")
    percentage = fields.Float(digits=(10, 4), string="Percentage")

    @api.onchange('product_id')
    def onchange_product_component(self):
        for rec in self:
            if rec.rnd_bom_id:
                rec.bom_id = rec.research_id.bom_id
            if rec.research_id:
                if not self.operation_id:
                    self.write({'operation_id': self.env['mrp.routing.workcenter'].search([('rnd_bom_id', '=', rec.bom_id.id)]).filtered
                    (lambda wo: wo.workcenter_id.id in self.env["inno.config"].sudo().search([],
                                                                                         limit=1).weaving_operation_id.ids)})


class MrpOperation(models.Model):
    _inherit = "mrp.routing.workcenter"

    rnd_workcenter = fields.Many2one(comodel_name="mrp.workcenter", string="Operation")
    research_id = fields.Many2one(comodel_name="inno.research", string="Research")
    rnd_bom_id = fields.Many2one(related="research_id.bom_id", string="Bom")

    @api.onchange('company_id')
    def onchange_product_component(self):
        for rec in self:
            if rec.rnd_bom_id:
                rec.bom_id = rec.research_id.bom_id


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    research_id = fields.Many2one(comodel_name="inno.research", string="Research")

    def button_action_views_for_research(self):
        return {
            'type': 'ir.actions.act_window',
            'name': _("Research"),
            'view_mode': 'form',
            'res_model': 'inno.research',
            'res_id': self.research_id.id,
            "target": "current",
        }

    def button_for_open_bracodes(self):
        barcodes=self.env['mrp.barcode'].search([('mrp_id', '=', self.id)])
        action = {
            'name': _(f"Barcodes"),
            'view_mode': 'form',
            'res_model': 'mrp.barcode',
            'type': 'ir.actions.act_window',
        }
        if len(barcodes) > 1:
            action.update({'view_mode': 'tree,form', 'domain': [('id', 'in', barcodes.ids)]})
        else:
            action.update({'view_type': 'form', 'res_id': barcodes[0].id})
        return action


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    research_id = fields.Many2one(comodel_name="inno.research", string="Research")


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    research_id = fields.Many2one(comodel_name="inno.research", string="Research")


class RndAttribute(models.Model):
    _inherit = 'rnd.master.data'

    def write(self, vals):
        admin_group = self.env.ref('inno_R_and_D.group_inno_rnd_admin').id
        if admin_group not in self.env.user.groups_id.ids:
            raise UserError(_("You Don't have access to edit this record.\nPlease ask your admin to update "
                              "this record"))
        return super().write(vals)


class Products(models.Model):
    _inherit = "product.product"

    @api.onchange('inno_mrp_size_id', 'inno_finishing_size_id', 'choti')
    def onchange_product_mrp_and_finishing_size(self):
        for rec in self:
            if rec.inno_mrp_size_id or rec.inno_finishing_size_id or rec.choti:
                line_id = self.env["inno.research.line"].search([('name', '=', rec.default_code)], limit=1)
                if line_id:
                    line_id.write({'manufacturing_size': rec.inno_mrp_size_id.id, 'finishing_size': rec.inno_finishing_size_id.id, 'choti': rec.choti})








