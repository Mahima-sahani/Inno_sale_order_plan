import datetime
from odoo import models, api
import logging
from odoo.exceptions import UserError

_logger = logging.getLogger(__name__)

class ReportMaterialIssue(models.AbstractModel):
    _name = 'report.inno_sale_order_plan.report_sale_order_inventory_status'
    _description = 'Sale Order Inventory Status Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        
        total_sale_order_qty = []
        total_pending_sale_order_qty = []
        total_stock_qty = []
        total_on_loom_qty = []
        total_to_be_issue_qty = []
        total_dispatched_qty = []
        total_packing = []

        overdue_days = {}
        today = datetime.date.today()

        docids = data.get('docids')
        to_date = data.get('to_date')
        from_date = data.get('from_date')
        buyer = data.get('buyer')
        order_type = data.get('order_type')
        report_for = data.get('report_for')
        filter = data.get('filter')
        report_pending_all = data.get('report_pending_all')
        
        report_unit = ""
         
        if report_for == 'area_wise':
            report_unit = "Area"
        if report_for == 'qty_wise':
            report_unit = "Quantity"
        if report_for == 'amt_wise':
            report_unit = "Amount"

        records = self.env['inno.sale.order.planning.line'].browse(docids).filtered(lambda rec: rec.sale_order_planning_id.sale_order_id.state not in ['cancel'])
        work_order_data = {}
        for rec in records:
            area = rec.product_id.mrp_area
            order_no = rec.sale_order_planning_id.order_no
            sale_order_no = rec.sale_order_planning_id.sale_order_id
            rate = rec.rate
            
            packaging = self.env['stock.quant'].search([('inno_sale_id', '=', sale_order_no.id),('product_id','=',rec.product_id.id),('inno_package_id','!=',False)])
            
            roll_on = [pack.roll_no for pack in packaging]
            
            inv = self.env['inno.packaging.invoice.line'].search([('roll_no', 'in', roll_on),('sale_order_id', '=', sale_order_no.id),('product_id','=',rec.product_id.id)])
            
            pack = len(packaging) - len(inv) if packaging else 0
            # total_packing.append(pack)

            dispatch_qty = self.env['inno.packaging.invoice.line'].search([('sale_order_id', '=', sale_order_no.id),('product_id','=',rec.product_id.id)])
            dispatched_qty = len(dispatch_qty) if dispatch_qty else 0
            # total_dispatched_qty.append(dispatched_qty)
            
            if report_for == "qty_wise":
                qty = 1
            elif report_for == "area_wise":
                qty = area
            elif report_for == "amt_wise":
                qty = rate

            data = {
                    'order_no': order_no,
                    'order_date': rec.sale_order_planning_id.order_date.strftime('%d/%b/%y') if rec.sale_order_planning_id.order_date else False,
                    'delivery_date': rec.sale_order_planning_id.due_date.strftime('%d/%b/%y') if rec.sale_order_planning_id.due_date else False,
                    'product': rec.product_id.default_code,
                    'sale_order_qty': int(rec.product_uom_qty * qty),
                    'pending_sale_order_qty': int(rec.product_uom_qty * qty) - dispatched_qty,
                    'packed': pack,
                    'dispatched': dispatched_qty
                    }

            # total_sale_order_qty.append(int(rec.product_uom_qty * qty))
            # total_pending_sale_order_qty.append(int(rec.product_uom_qty * qty) - dispatched_qty)


            due_date = rec.sale_order_planning_id.due_date
            if due_date:
                if today < due_date:
                    days_overdue = (today - due_date).days
                    overdue_days[order_no] = days_overdue
                else:
                    days_overdue = (today - due_date).days
                    overdue_days[order_no] = days_overdue

            if report_pending_all == 'pending':
                if data.get('sale_order_qty') != data.get('dispatched'):
                    work_orders = self.env['mrp.workorder'].search([('name', '=', 'Weaving'),('sale_id', '=', sale_order_no.id),('product_id','=',rec.product_id.id)])
                    for work_order in work_orders:
                        if work_order:
                            data['stock']= int(work_order.finished_qty * qty) - dispatched_qty
                            data['to_be_issue']= int(work_order.remaining_to_allocate * qty) 
                            barcode = self.env['mrp.barcode'].search([('current_process','=',work_order.id),('state','not in',['1_draft'])])
                            data['on_loom'] = len(barcode) * qty
                            total_on_loom_qty.append(len(barcode) * qty)

                            if work_order.id not in work_order_data:
                                work_order_data[work_order.id] = []
                            work_order_data[work_order.id].append(data)

                            total_stock_qty.append(int(work_order.finished_qty * qty) - dispatched_qty)
                            total_to_be_issue_qty.append(int(work_order.remaining_to_allocate * qty))

                    purchase_order_line = self.env['purchase.order.line'].search([('product_id','=',rec.product_id.id)])
                    if purchase_order_line:
                        for line in purchase_order_line:
                            ss = line.move_ids.move_dest_ids.group_id.sale_id.mapped('order_no')
                            if order_no in ss:
                                data['on_loom'] = int(line.product_qty - line.qty_received) * qty
                                data['stock']= int(line.qty_received  * qty) - dispatched_qty
                                data['to_be_issue']= 0

                                if line.id not in work_order_data:
                                    work_order_data[line.id] = []
                                work_order_data[line.id].append(data)

                                total_on_loom_qty.append(int(line.product_qty - line.qty_received * qty))
                                total_stock_qty.append(int(line.qty_received * qty) - dispatched_qty)
                                total_to_be_issue_qty.append(int(0))
                    total_dispatched_qty.append(dispatched_qty)
                    total_packing.append(pack)
                    total_sale_order_qty.append(int(rec.product_uom_qty * qty))
                    total_pending_sale_order_qty.append(int(rec.product_uom_qty * qty) - dispatched_qty)
                # else:
                #     raise UserError("All Quantites has been Dispatched")

            else:
                work_orders = self.env['mrp.workorder'].search([('name', '=', 'Weaving'),('sale_id', '=', sale_order_no.id),('product_id','=',rec.product_id.id)])
                for work_order in work_orders:
                    if work_order:
                        data['stock']= int(work_order.finished_qty * qty) - dispatched_qty
                        data['to_be_issue']= int(work_order.remaining_to_allocate * qty) 
                        barcode = self.env['mrp.barcode'].search([('current_process','=',work_order.id),('state','not in',['1_draft'])])
                        data['on_loom'] = len(barcode) * qty
                        total_on_loom_qty.append(len(barcode) * qty)


                        if work_order.id not in work_order_data:
                            work_order_data[work_order.id] = []
                        work_order_data[work_order.id].append(data)

                        total_stock_qty.append(int(work_order.finished_qty * qty) - dispatched_qty)
                        total_to_be_issue_qty.append(int(work_order.remaining_to_allocate * qty))

                purchase_order_line = self.env['purchase.order.line'].search([('product_id','=',rec.product_id.id)])
                if purchase_order_line:
                    for line in purchase_order_line:
                        ss = line.move_ids.move_dest_ids.group_id.sale_id.mapped('order_no')
                        if order_no in ss:
                            data['on_loom'] = int(line.product_qty - line.qty_received) * qty
                            data['stock']= int(line.qty_received  * qty) - dispatched_qty
                            data['to_be_issue']= 0
                            if line.id not in work_order_data:
                                work_order_data[line.id] = []
                            work_order_data[line.id].append(data)

                            total_on_loom_qty.append(int(line.product_qty - line.qty_received * qty))
                            total_stock_qty.append(int(line.qty_received * qty) - dispatched_qty)
                            total_to_be_issue_qty.append(int(0))
                total_dispatched_qty.append(dispatched_qty)
                total_packing.append(pack)
                total_sale_order_qty.append(int(rec.product_uom_qty * qty))
                total_pending_sale_order_qty.append(int(rec.product_uom_qty * qty) - dispatched_qty)

        if not records:
            raise UserError("Record does not exist")
        data = {
            'work_order_data': [work_data for key,work_data in work_order_data.items()],
            'overdue_days':overdue_days,
            'total_sale_order_qty' : sum(total_sale_order_qty),
            'total_pending_sale_order_qty' : sum(total_pending_sale_order_qty),
            'total_stock_qty' : sum(total_stock_qty),
            'total_on_loom_qty' : sum(total_on_loom_qty),
            'total_to_be_issue_qty' : sum(total_to_be_issue_qty),
            'total_dispatched_qty' : sum(total_dispatched_qty),
            'to_date': to_date,
            'from_date': from_date,
            'report_unit': report_unit,
            'filter': filter,
            'total_packing': sum(total_packing),
            'report_pending_all':report_pending_all.capitalize()
        }
        return {
            'doc_ids': docids,
            'doc_model': 'inno.sale.order.planning',
            'docs': records,
            'data': data
        }
