from odoo import http,tools, _
from odoo.http import request
from datetime import datetime


class MrpDataController(http.Controller):

    def create_request_data(self, operation, uid=False):
        values = {
            'user_id': uid if uid else request.context.get('uid'),
            'operation': operation,
            'date': datetime.now()
        }
        if request.params:
            values.update({'requested_data': request.params})
        return request.env['api.request'].sudo().create(values)

    @http.route('/user_logout', type='http', auth="user", methods=['GET'])
    def user_logout(self):
        request_record = self.create_request_data(operation='logout')
        request.session.logout()
        request_record.status = 'success'
        return "success"

    @http.route('/barcode_user_access', type='json', auth="public", methods=['POST'])
    def get_user_access_data(self):
        db = request.cr.dbname
        user = request.params.get('login')
        password = request.params.get('password')
        uid = request.session.authenticate(db, user, password)
        request_record = self.create_request_data(operation='login', uid=uid)
        if not uid:
            request_record.status = 'failed'
            return {'status': 'failed', 'reason': 'Authentication Failed'}
        user = request.env['user.access'].search([('user_id', '=', uid)])
        if user:
            request_record.status = 'success'
            return {'status': 'success', 'user_id': uid, 'bazaar_receiving': user.bazaar_receiving,
                    'bazaar_qa_verification': user.bazaar_qa_verification}
        else:
            request_record.status = 'failed'
            return {'status': 'failed', 'reason': 'No such user access found'}

    @http.route('/bazaar_receiving', type='json', auth="user", methods=['POST'])
    def get_main_job_works(self):
        request_record = self.create_request_data(operation='receiving')
        try:
            barcodes = request.env['mrp.barcode'].search([('name', 'in', request.params.get('barcodes', []))])
            if not barcodes:
                raise Exception('No Barcode Found in the records')
            wrong_barcodes, barcodes = self.verify_barcodes(barcodes, operation='receiving')
            if not barcodes:
                raise Exception('The operation is now allowed to the given barcodes. Please verify and try again.')
            main_job_work_ids = barcodes.main_job_work_id.ids
            self.create_main_bazaar(main_job_work_ids, barcodes)
        except Exception as ex:
            request_record.status = 'failed'
            return {'status': 'failed', 'reason': ex}
        response = {'status': 'partial', 'barcode_issue': wrong_barcodes.mapped('name')} if wrong_barcodes \
            else {'status': 'success'}
        request_record.status = 'success'
        return response

    @http.route('/bazaar_qa_verification', type='json', auth="user", methods=['POST'])
    def bazaar_qa_verification(self):
        request_record = self.create_request_data(operation='qa')
        try:
            barcodes = request.env['mrp.barcode'].search([('name', 'in', request.params.get('barcodes', []))])
            wrong_barcodes, barcodes = self.verify_barcodes(barcodes, operation='qa_verification')
            weights = request.params.get('weights', [])
            if not barcodes:
                raise Exception('Products already Verified')
            main_bazaars = barcodes.bazaar_id
            self.verify_main_bazaar(main_bazaars, barcodes, weights)
        except Exception as ex:
            request_record.status = 'failed'
            return {'status': 'failed', 'reason': ex}
        response = {'status': 'partial', 'barcode_issue': wrong_barcodes.mapped('name')} if wrong_barcodes \
            else {'status': 'success'}
        request_record.status = 'success'
        return response

    @staticmethod
    def verify_barcodes(barcodes, operation):
        wrong_barcodes = False
        if operation == 'receiving':
            wrong_barcodes = barcodes.filtered(lambda bcode: bcode.state not in ['3_allocated', '6_rejected'])
        elif operation == 'qa_verification':
            wrong_barcodes = barcodes.filtered(lambda bcode: bcode.state != '4_received')
        return wrong_barcodes, barcodes.filtered(lambda bcode: bcode.id not in wrong_barcodes.ids)

    def create_main_bazaar(self, main_job_work_ids, barcodes):
        record = request.env['main.baazar'].sudo().create({'main_jobworks_ids': main_job_work_ids, 'date': datetime.now()})
        record.add_sub_name()
        record.button_action_for_alloted_bazazr_product()
        jobworks = record.baazar_lines_ids.mapped('job_work_id')
        products = {jobwork.id: len(jobwork.barcodes.filtered(lambda bcode: bcode.id in barcodes.ids))for jobwork in jobworks}
        for line in record.baazar_lines_ids:
            line.receive_product_qty = products.get(line.job_work_id.id) or 0
            line.do_confirm()
        barcodes.sudo().write({'state': '4_received', 'bazaar_id': record.id})

    def verify_main_bazaar(self, main_bazaars, barcodes, weights):
        barcodes.sudo().write({'state': '5_verified'})
        for bazaar in main_bazaars:
            jobworks = bazaar.baazar_lines_ids.mapped('job_work_id')
            products = {jobwork.id: len(jobwork.barcodes.filtered(lambda bcode: bcode.id in barcodes.ids)) for jobwork
                        in jobworks}
            for line in bazaar.baazar_lines_ids:
                line.accepted_qty = products.get(line.job_work_id.id) or 0
                line.do_process()
                associated_barcodes = line.job_work_id.barcodes.filtered(lambda bcode: bcode.id in barcodes.ids)
                line.actual_weight = sum([float(weights.get(bcode)) for bcode in associated_barcodes.mapped('name')])
                associated_barcodes.write({'bazaar_line_id': line.id})
                line.verify_job_work_line()

    @http.route('/get_barcode_status', type='http', auth="user", methods=['GET'])
    def get_barcode_status(self):
        barocde = request.env['mrp.barcode'].search([('name', '=', request.params.get('barcode'))], limit=1)
        return f"{barocde.current_process.name}"
