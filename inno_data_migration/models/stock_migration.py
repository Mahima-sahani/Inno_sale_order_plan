from odoo import models, fields, api, _


class StockMigration(models.Model):
    _name = 'inno.stock.migration'
    _rec_name = 'product_id'

    product_id = fields.Many2one(comodel_name='product.product', string='Product')
    location_id = fields.Many2one(comodel_name='stock.location', string='Location')
    issue_qty = fields.Float(digits=(8, 3), string='Issue Qty')
    rec_qty = fields.Float(digits=(8, 3), string='Receive Qty')
    opening = fields.Float(digits=(8, 3), string='Opening')
    balance = fields.Float(digits=(8, 3), string='Balance')
    synced = fields.Selection(string='Synced', selection=[('synced', 'Synced'), ('not_synced', 'Not Synced')],
                              default='not_synced')

    def sync_stock_all(self):
        for rec in self.search([('synced', '!=', 'not_synced')]):
            self.sync_stock()

    def sync_stock(self):
        try:
            if self._context.get('sync_opening'):
                stock = self.env['stock.quant'].search([('product_id', '=', self.product_id.id), ('location_id', '=', self.location_id.id)])

                self.env['stock.quant']._update_available_quantity(self.product_id, self.location_id, -stock.quantity)
                self.env['stock.quant']._update_available_quantity(self.product_id, self.location_id, self.balance)
                stock.opening = self.opening
            else:
                self.env['stock.quant']._update_available_quantity(self.product_id, self.location_id,
                                                                   (self.rec_qty-self.issue_qty))
            self.write({'synced': 'synced', 'rec_qty': 0, 'issue_qty': 0})
        except Exception as ex:
            pass
