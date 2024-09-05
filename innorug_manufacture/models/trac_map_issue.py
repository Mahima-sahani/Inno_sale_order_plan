from odoo import models, fields, api, _


class TraceMap(models.Model):
    _name = 'inno.trace.map'
    _description = 'Trace map Per Subcontractor'

    partner_id = fields.Many2one(comodel_name='res.partner', string='Subcontractor')
    trace_map_line_ids = fields.One2many(comodel_name='inno.trace.map.line', inverse_name='trace_map_id')
    move_ids = fields.Many2many(comodel_name='stock.move')


class TraceMapLine(models.Model):
    _name = 'inno.trace.map.line'

    trace_map_id =  fields.Many2one(comodel_name='inno.trace.map')
    product_id = fields.Many2one(comodel_name='product.product', string='TRACE/MAP')
    quantity = fields.Integer(string='Quantity')
    trace_map = fields.Selection(selection=[('trace', 'Trace'), ('map', 'Map')])
