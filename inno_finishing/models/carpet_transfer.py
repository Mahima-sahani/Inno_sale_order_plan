from odoo import models, fields, api,_
from odoo.exceptions import UserError, ValidationError, MissingError
import base64


class CarpetTransfer(models.Model):
    _name = 'inno.carpet.transfer'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Manages the record of carpet transfer'
    _rec_name = "name"

    name = fields.Char(default='/')
    source_location_id = fields.Many2one(comodel_name='stock.location', string="Source Location")
    dest_location_id = fields.Many2one(comodel_name='stock.location', string="Destination Location")
    state = fields.Selection(selection=[('draft', 'Waiting for Transfer'),('gpass', 'Waiting for Transfer'), ('transit', 'In Transit'),
                                        ('partial', 'Partial Received'),
                                        ('done', 'Transferred'), ('cancel', 'Cancel')], default='draft', tracking=True)
    color = fields.Integer(compute='compute_kanban_color', default=2)
    person_id = fields.Many2one(comodel_name="res.partner", string="Person")
    remarks = fields.Text(string="Remarks")
    issue_date = fields.Datetime(default=fields.Datetime.now, string="Date")
    barcode_id = fields.Many2one(comodel_name='mrp.barcode')
    display_warning = fields.Boolean()
    total_transfer_qty = fields.Integer("qty", compute='_get_count')
    total_received_qty = fields.Integer("qty", compute='_get_count')
    barcode_line = fields.One2many("barcode.line", "transfer_id", string="Barcode")
    company_id = fields.Many2one(comodel_name='res.company')

    def action_cancel(self):
        for rec in self:
            rec.barcode_line.barcode_id.write({'transfer_id': False,
                                    'location_id': rec.source_location_id.id})
            rec.state = 'cancel'

    @api.depends('barcode_line')
    def _get_count(self):
        for rec in self:
            trs_qty = rec.barcode_line.filtered(lambda bcode: bcode.location_id == self.source_location_id).ids
            trs_rcv = rec.barcode_line.filtered(lambda bcode: bcode.location_id == self.dest_location_id).ids
            rec.total_transfer_qty = len(trs_qty)
            rec.total_received_qty = len(trs_rcv)

    @api.onchange('barcode_id')
    def onchange_barcodes(self):
        if self.dest_location_id and self.source_location_id:
            if self.state == 'draft':
                bcode = self.env["mrp.barcode"].search(
                    [('location_id', '=', self.source_location_id.id),
                     ('state', 'in', ['5_verified', '7_finishing', '8_done','9_done']),
                     ('id', '=', self.barcode_id.id)])
                barcode = bcode.filtered(lambda bcode: bcode.id not in self.barcode_line.barcode_id.ids and not bcode.finishing_jobwork_id and not bcode.current_process)
                if barcode and not barcode.transfer_id :
                    t =self.browse(self.id.origin).write({'barcode_line': [(0, 0, {
                        'barcode_id': barcode.id,
                        'transfer_id': self.id,
                    })]})
                    barcode.update({'transfer_id': self.id.origin})
                    self._cr.commit()
                    self.display_warning = False
                    self.barcode_id = False
                else:
                    self.display_warning = True
                    self.barcode_id = False
            else:
                if self.state == "transit" or self.state == "partial":
                    line_id = self.barcode_line.filtered(lambda bcode: self.barcode_id.id in bcode.barcode_id.ids)
                    if line_id and line_id.barcode_id.location_id != self.dest_location_id:
                        line_id.barcode_id.location_id = self.dest_location_id.id
                        line_id.barcode_id.transfer_id = False
                        self._cr.commit()
                        self.display_warning = False
                        self.barcode_id = False
                        if len(self.browse(self.id.origin).barcode_line.mapped("location_id").ids) == 1:
                            self.state = "done"
                        else:
                            self.state = 'partial'
                    else:
                        self.barcode_id = False
                        self.display_warning = True

    def change_transfer_status(self, barcodes):
        if barcodes:
            for rec in barcodes:
                rec.write({'location_id': rec.transfer_id.dest_location_id.id})
                if len(rec.transfer_id.barcode_line.mapped("location_id").ids) == 1:
                    rec.transfer_id.state = "done"
                else:
                     rec.transfer_id.state= 'partial'
            return True
        return False



    @api.model
    def default_get(self, fields_list):
        rec = super().default_get(fields_list)
        if rec.get('name') == '/':
            rec.update({'name': self.env['ir.sequence'].next_by_code('carpet_transfer_seq') or '/'})
        return rec

    def open_transfer_barcode(self):
        pass

    def open_received_barcodes(self):
        pass

    def compute_kanban_color(self):
        for rec in self:
            rec.color = 2 if rec.state == 'draft' else 4 if rec.state == 'done' else 10

    def generate_gate_pass(self):
        """
        This method will generate a gate pass for carpet transfer
        """
        if self.barcode_line:
            if not self.company_id:
                self.company_id = False
            pdf = self.env.ref('inno_finishing.action_report_material_gate_pass',
                               )._render_qweb_pdf('inno_finishing.''action_report_material_gate_pass',
                                                                                 res_ids=self.id)[0]
            pdf = base64.b64encode(pdf).decode()
            attachment = self.env['ir.attachment'].create({'name': f"Gate Pass: {self.name}",
                                                           'type': 'binary',
                                                           'datas': pdf,
                                                           'res_model': 'inno.carpet.transfer',
                                                           'res_id': self.id,
                                                           })
            self.message_post(body="Gate Pass Generated", attachment_ids=[attachment.id])
            self.state = "transit"

    def transfer_confirm(self):
        """
        This method will transfer the barcodes to other location
        """
        for rec in self:
            if not rec.barcode_line:
                raise UserError(_("First you can scan the carpet barcode and then confirm it"))
            rec.state = 'gpass'
            self.display_warning = False

    def action_force_transfer(self):
        self.barcode_line.barcode_id.filtered(lambda bcode: bcode.location_id.id == 19).write({
            'location_id': self.dest_location_id.id,'transfer_id': False})
        self.message_post(body="<b style='color: red;'> Forcefully transferred the carpets</b>")
        self.state = 'done'

    def remove_transfer_no(self):
        for rec in self:
            for line in rec.barcode_line.barcode_id:
                line.write({'transfer_id': False})

