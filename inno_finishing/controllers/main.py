from odoo import http,tools, _
from odoo.http import request
from datetime import datetime

class MrpFinishingController(http.Controller):

    def create_request_data(self, operation, uid=False):
        values = {
            'user_id': uid if uid else request.context.get('uid'),
            'operation': operation,
            'date': datetime.now()
        }
        if request.params:
            values.update({'requested_data': request.params})
        return request.env['api.request'].sudo().create(values)

    @http.route('/finishing', type='json', auth="user", methods=['POST'])
    def generate_finishing_request(self):
        request_record = self.create_request_data(operation='finishing')
        try:
            operation, barcodes, subcontractor, is_external = (request.env['mrp.workcenter'].sudo().browse(int(request.params.get('operation', False))),
                                                               request.env['mrp.barcode'].search([
                                                                   ('name', 'in', request.params.get('barcode', []))]),
                                                               request.params.get('subcontractor', False),
                                                               request.params.get('is_external', False))
            if not barcodes:
                raise Exception('No Barcode Found in the records')
            right_barcodes = barcodes.filtered(lambda bcode: operation.id in
                                                             bcode.sudo().mrp_id.workorder_ids.workcenter_id.ids
                                                             and operation.id not in bcode.sudo().process_finished.ids
                                                             and operation.id != bcode.sudo().current_process.id
                                                             and bcode.full_finishing == False)
            self.finishing_operation(operation.id, right_barcodes, subcontractor, is_external)
            wrong_barcodes = {bcode.name: bcode.sudo().current_process.name for bcode in barcodes if bcode not in right_barcodes}
        except Exception as ex:
            request_record.status = 'failed'
            return {'status': 'failed', 'reason': ex}
        response = {'status': 'partial', 'barcode_issue': wrong_barcodes} if wrong_barcodes \
            else {'status': 'success'}
        request_record.status = 'success'
        return response

    @http.route('/finishing_order', type='json', auth="user", methods=['POST'])
    def generate_finishing_order_rcvd_request(self):
        request_record = self.create_request_data(operation='final_rcvd')
        try:
            order, barcodes = (
            request.env['finishing.work.order'].sudo().browse(int(request.params.get('orders', False))),
            request.params.get('barcode'))
            # for key v in barcodes:
            #     print(key)

        except Exception as ex:
            request_record.status = 'failed'
            return {'status': 'failed', 'reason': ex}
        request_record.status = 'success'


    @http.route('/finishing_receive', type='http', auth="user", methods=['GET'])
    def generate_finishing_rcvd(self):
        request_record = self.create_request_data(operation='request_rcvd')
        order = request.params.get('order')
        try:
            if bool(int(order)):
                recs = {order.name: order.id for order in request.env['finishing.work.order'].sudo().search([]) if
                        order.status == 'processing' or  order.status == '1_received'}
                if recs:
                    request_record.status = 'success'
                    return f"'status': 'success', Data : ['orders' : {recs}]"
        except Exception as ex:
            request_record.status = 'failed'
            return {'status': 'failed', 'reason': ex}

    @http.route('/fullfinishing', type='json', auth="user", methods=['POST'])
    def generate_full_finishing_request(self):
        barcodes, subcontractor, full_finishing = (request.env['mrp.barcode'].search([
            ('name', 'in', request.params.get('barcode', []))]), request.params.get('sub'),
                                                   request.params.get('full_finishing'))
        accurate_bcodes = barcodes.filtered(lambda bcode: bcode.state == '5_verified'and bcode.full_finishing == False)
        operation = 11
        finishing_id = False
        is_external = True
        if accurate_bcodes:
            finishing_id = self.finishing_operation(operation, accurate_bcodes, subcontractor, is_external)
            for bcode in accurate_bcodes:
                bcode.full_finishing = True
                bcode.current_process = operation
        wrong_bcodes = {bcode.name: bcode.sudo().current_process.name for bcode in barcodes if bcode not in accurate_bcodes}
        if wrong_bcodes:
            return {"status" : 'pending','wrong' : wrong_bcodes}
        else:
            if finishing_id :
                return {'status': 'success'}
            else:
                return {'status': 'Never barcode present for finishing process'}

    @staticmethod
    def finishing_operation(operation, barcodes, subcontractor, external, location = False):
        operation_id = request.env['mrp.workcenter'].sudo().browse(int(operation))
        vals = {"name" : operation_id.sequence_id.next_by_id(), 'operation_id': operation_id.id,
                "barcodes": [(6, 0, barcodes.ids)]}
        if subcontractor:
            vals.update({'is_external': external, "subcontractor_id": int(subcontractor)})
        else:
            if location:
                vals.update({'location_id': location})
        finishing_id = request.env['finishing.work.order'].sudo().create(vals)
        return finishing_id

    @http.route('/transfer', type='json', auth="user", methods=['POST'])
    def generate_transfer_request(self):
        request_record = self.create_request_data(operation='transfer_validate')
        try:
            barcodes, person, building, remarks = (request.env['mrp.barcode'].search([
                ('name', 'in', request.params.get('barcode', []))]), request.params.get('person'),
                                                       request.params.get('building'),
                                                       request.params.get('remarks'))
            bcodes = barcodes.filtered(lambda bcode: bcode.state in ['5_verified', '7_finishing','8_packaging', '9_done'])
            if bcodes :
                location = bcodes.mapped("location_id").ids
                print(location)
                division = bcodes.mapped("division_id").ids
                print(division)
                if len(division) == 1 and len(location)==1:
                    blocation = {code.name: code.sudo().location_id.name for code in bcodes}
                    if (bcodes.mapped("location_id").id != int(building)):
                        transfer = self.create_transfer(bcodes, person, building, remarks)
                        if transfer:
                            request_record.status = 'success'
                            return {'status': 'success'}
                    else:
                        request_record.status = 'Already Transfer'
                        return {'status': 'Already Transfer', "Details" : blocation }
                else:
                    request_record.status = 'Failed'
                    return {'status': 'Failed'}
            else:
                if not bcodes:
                    return {'status': 'Failed', "message" : "Upload barcode"}
        except Exception as ex:
            request_record.status = 'failed'
            return {'status': 'failed', 'reason': ex}

    @staticmethod
    def create_transfer(bcodes, person, building, remarks):
        transfer = False
        building_id = request.env['stock.location'].sudo().browse(int(building))
        person_id = request.env['res.partner'].sudo().browse(int(person))
        vals = {'remarks': remarks, 'person_id': person_id.id, 'state': 'draft',
                "source_location_id" : bcodes.mapped("location_id").id, "dest_location_id" : building_id.id,
                "barcodes": [(6, 0, [v.id for v in (bcodes)])]}
        if vals:
            transfer = request.env['inno.carpet.transfer'].sudo().create(vals)
        return transfer

    @http.route('/transfer_validate', type='json', auth="user", methods=['POST'])
    def generate_transfer_validate(self):
        request_record = self.create_request_data(operation='transfer_validate')
        try :
            barcodes, transfer= (request.env['mrp.barcode'].search([
                ('name', 'in', request.params.get('barcode', []))]), request.env['inno.carpet.transfer'].search([
                ('id', '=', request.params.get('id'))]))
            if barcodes:
                right_barcodes = barcodes.filtered(lambda bcode: bcode.id in transfer.barcodes.ids and
                                                                 bcode.location_id.id != transfer.dest_location_id.id)
                right_barcodes.write({'location_id': transfer.dest_location_id.id})
                if right_barcodes:
                    if len(transfer.barcodes.mapped('location_id').ids) == 1:
                        transfer.state = 'done'
                    else:
                        transfer.state = '1_transit'
                request_record.status = 'success'
                return barcodes.filtered(lambda bcode: bcode.id not in right_barcodes.ids and
                                               bcode.location_id.id != transfer.dest_location_id.id).mapped('name')
        except Exception as ex:
                request_record.status = 'failed'
                return {'status': 'failed', 'reason': ex}

    @http.route('/transfer_receive', type='http', auth="user", methods=['GET'])
    def generate_transfer_receive(self):
        request_record = self.create_request_data(operation='transfer_receive')
        transfer = request.params.get('receive')
        try:
            if bool(int(transfer)):
                recs = {order.name: order.id for order in request.env['inno.carpet.transfer'].sudo().search([]) if
                        order.state == 'transit'}
                if recs:
                    request_record.status = 'success'
                    return f"'status': 'success', Data : ['persons' : {recs}]"
        except Exception as ex:
            request_record.status = 'failed'
            return {'status': 'failed', 'reason': ex}

    @http.route('/transfer_data', type='http', auth="user", methods=['GET'])
    def generate_transfer_date(self):
        request_record = self.create_request_data(operation='transfer_data')
        transfer = request.params.get('transfer')
        try:
            if bool(int(transfer)):
                location = {order.name: order.id for order in request.env['stock.location'].sudo().search([])}
                records = {order.name: order.id for order in request.env['res.partner'].sudo().search([])}
                request_record.status = 'success'
                return f"'status': 'success', Data : ['persons' : {records}  , 'location' : {location}]"
        except Exception as ex:
            request_record.status = 'failed'
            return {'status': 'failed', 'reason': ex}

    @http.route('/fetch_barcode_details', type='http', auth="user", methods=['GET'])
    def get_operation(self):
        """
        Get details of barcode to api
        """
        barcodes = request.params.get('barcode')
        barcode_id = request.env['mrp.barcode'].search([
            ('name', '=', barcodes),
        ], limit=1)
        records = {order.name: order.id for order in barcode_id.sudo().mrp_id.workorder_ids.workcenter_id
                   if order.id not in barcode_id.process_finished.ids}
        records["State"] = barcode_id.state
        return f"{records}"

    @http.route('/full_finishing_issue', type='http', auth="user", methods=['GET'])
    def full_finishing_issue(self):
        issue = request.params.get('issue')
        if issue:
            operation_id = request.env['mrp.workcenter'].sudo().search([
                ('id', '=', int(11)),
            ])
            t = "subcontractor"
            oper = "Operation"
            records = {order.name: order.id for order in request.env['res.partner'].sudo().search([])}
            print(records)
            return f"{records}"

    @http.route('/fetch_location_lists', type='http', auth="user", methods=['GET'])
    def fetch_location_lists(self):
        location, operation = request.params.get('location'), request.params.get('operation')
        if location:
            operation_id = request.env['mrp.workcenter'].sudo().search([
                ('id', '=', int(operation)),
            ])
            if operation_id:
                records = {order.name: order.id for order in operation_id.location_id}
                return f"{records}"
        if not location:
            records = {order.name: order.id for order in request.env['res.partner'].sudo().search([])}
            return f"{records}"

    @http.route('/finishing_operation_lists', type='http', auth="user", methods=['GET'])
    def finishing_operation_lists(self):
        finishing = request.params.get('finishing')
        if finishing :
            operation_lists = request.env['mrp.workcenter'].sudo().search([
                ('is_finishing_wc', '=', True),
            ])
            if operation_lists:
                records = {order.name: order.id for order in operation_lists}
                return f"{records}"
            if not operation_lists:
                return "No Finishing Operation"

