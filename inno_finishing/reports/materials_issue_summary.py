import datetime
from odoo import models, api, _
from odoo.exceptions import UserError, ValidationError, MissingError


class ReportMaterialIssueSummaryReport(models.AbstractModel):
    _name = 'report.inno_finishing.materials_issue_summary'
    _description = 'Will Provide the report of all finishing material issue summary'

    @api.model
    def _get_report_values(self, docids, data=None):
        sub_data = []
        new_data = {}
        domain = []
        operation_id = self.env['mrp.workcenter'].sudo().search([('id', '=', int(data.get('operation_id')))])
        date_from = data.get('from_date')
        subcontractor_id = data.get('subcontractor_id')
        if subcontractor_id:
            domain += [('subcontractor_id', '=', int(subcontractor_id))]
        if date_from:
            domain += [('issue_date', '>=', date_from)]
        date_to = data.get('to_date')
        if date_to:
            domain += [('issue_date', '<=', date_to)]
            new_data.update({'to_date': data.get('to_date'),
                             'from_date': data.get('from_date'), 'data': 'yes'})
        work_orders = self.env['finishing.work.order'].sudo().search(domain).filtered(lambda dv: dv.division_id.id
                                                                                                 in self.env.user.division_id.ids
                                                                                                 and dv.operation_id.id == operation_id.id and dv.material_lines)
        total_newar = 0.0
        polyster_yarn = 0.0
        total_silk = 0.0
        third_bck = 0.0
        woolen_yarn = 0.0
        total = 0.0
        order_dict = {}
        order_dict['vendor'] = ''
        all_types = {'yarn': 'YARN', 'cloth': 'CLOTH', 'wool': 'WOOL', 'acrlicy_yarn': 'ACRLICY YARN',
                     'jute_yarn': 'JUTE YARN', 'polyster_yarn': 'POLYSTER YARN',
                     'wool_viscose_blend': 'WOOL VISCOSE BLEND',
                     'woolen_febric': 'WOOLEN FEBRIC', 'imported': 'IMPORTED', 'cotten_dyes': 'COTTON DYES',
                     'third_backing_cloth': 'THIRD BACKING CLOTH', 'silk': 'SILK', 'tar': 'TAR',
                     'tharri': 'THARRI',
                     'lefa': 'LEFA', 'polypropylene': 'POLYPROPYLENE', 'nylon': 'NYLON', 'aanga': 'AANGA',
                     'ready_latex_chemical': 'READY LATEX CHEMICAL', 'latex': 'LATEX',
                     'cloth_cutting': 'CLOTH CUTTING',
                     'newar': 'NEWAR', 'other_raw_materials': 'OTHER RAW MATERIAL',
                     'weaving_cloth': 'WEAVING CLOTH', 'cotton_cone': 'COTTON CONE', 'other': 'OTHER',
                     'cotton': 'COTTON'}
        type_list = ['yarn', 'cloth', 'wool', 'acrlicy_yarn',
                     'jute_yarn', 'polyster_yarn',
                     'wool_viscose_blend',
                     'woolen_febric', 'imported', 'cotten_dyes',
                     'third_backing_cloth', 'silk', 'tar',
                     'tharri',
                     'lefa', 'polypropylene', 'nylon', 'aanga',
                     'ready_latex_chemical', 'latex',
                     'cloth_cutting',
                     'newar', 'other_raw_materials',
                     'weaving_cloth', 'cotton_cone', 'other', 'cotton']


        total_deliveries = self.env['stock.picking'].search([('finishing_work_id', 'in', work_orders.ids),
                                                             ('state', '=', 'done')]).filtered(
            lambda op: op.picking_type_id.code in ['outgoing', 'internal'])
        present_group = []
        for typ in type_list:
            if total_deliveries.move_ids.filtered(lambda mi: mi.product_id.product_tmpl_id.raw_material_group == typ):
                # order_dict[all_types.get(typ)] = ''
                present_group.append(all_types.get(typ))

        if work_orders:
            for sb in work_orders.subcontractor_id:
                vendor_wise = work_orders.filtered(lambda vd: sb.id in vd.subcontractor_id.ids)
                deliveries = self.env['stock.picking'].search([('finishing_work_id', 'in', vendor_wise.ids),
                                                               ('state', '=', 'done')]).filtered(
                    lambda op: op.picking_type_id.code in ['outgoing', 'internal'])
                newar = round(sum(deliveries.move_ids.filtered(
                    lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'newar').mapped(
                    'quantity_done')), 3)
                total_newar += newar
                polyster = round(sum(deliveries.move_ids.filtered(
                    lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'polyster_yarn').mapped(
                    'quantity_done')), 3)
                polyster_yarn += polyster
                silk = round(sum(deliveries.move_ids.filtered(
                    lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'silk').mapped(
                    'quantity_done')), 3)
                total_silk += silk
                third = round(sum(deliveries.move_ids.filtered(
                    lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'third_backing_cloth').mapped(
                    'quantity_done')), 3)
                third_bck += third
                wool = round(sum(deliveries.move_ids.filtered(
                    lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'wool').mapped(
                    'quantity_done')), 3)
                woolen_yarn += wool
                totl = round(sum(deliveries.move_ids.mapped(
                    'quantity_done')), 3)
                total += totl
                sub_data.append(
                    {'vendor': sb.name, 'Newar': newar, 'Polyster Yarn': polyster, 'Silk': silk,
                     'Third Backing Cloth': third,
                     'Woolen Yarn': wool, 'total': totl})
        records = self.env['finishing.baazar'].sudo().browse(1)
        if sub_data and work_orders:
            new_data.update(
                {'sub_data': sub_data, 'division': ', '.join(self.env.user.division_id.mapped('name')) if
                self.env.user.division_id else 'Main', 'site': 'Main', 'process': operation_id.name,
                 'total_newar': round(total_newar, 3),
                 'polyster_yarn': round(polyster_yarn, 3),
                 'total_silk': round(total_silk, 3),
                 'third_bck': round(third_bck, 3),
                 'woolen_yarn': round(woolen_yarn, 3),
                 'total': round(total, 3),
                 'groups' : ', '.join(present_group)
                 })
        return {
            'doc_ids': docids,
            'doc_model': 'finishing.baazar',
            'docs': records,
            'data': new_data, }
