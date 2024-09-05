from odoo import models, api


class ReportJobWorkReIssue(models.AbstractModel):
    _name = 'report.innorug_manufacture.report_cost_center_record'
    _description = 'Cost Center Report'


    @api.model
    def _get_report_values(self, docids, data=None):
        record = self.env['main.jobwork'].browse(docids)
        company = self.env['res.company'].search([], limit=1)
        bazaar_rec = dict()
        material_rec = []
        material_summ_rec = []
        account_summ_rec = []
        amount_cr = 0.0
        balance = 0.0
        consuption = []
        excess = []
        fix_incentive = 0.00

        for rec in record.baazar_lines_ids:
            for pr in rec.baazar_lines_ids.filtered(lambda bl: bl.state == 'verified').product_id:
                # for line in rec.baazar_lines_ids.filtered(lambda bl: bl.state == 'verified'):
                bz_lines = rec.baazar_lines_ids.filtered(
                    lambda bl: bl.state == 'verified' and pr.id in bl.product_id.ids)
                if bz_lines:
                    inc = 0.0
                    ord_inc = 0.0
                    baz_pen = 0.00
                    for br in bz_lines:
                        inc += sum(br.barcode.pen_inc_ids.filtered(lambda pl: pl.type == 'incentive').mapped('amount'))
                        ord_inc += sum(
                            br.barcode.pen_inc_ids.filtered(lambda pl: pl.type == 'time_incentive').mapped('amount'))
                        baz_pen += sum(
                            br.barcode.pen_inc_ids.filtered(
                                lambda pl: pl.type in ['time_penalty', 'bazaar_penalty', 'qa_penalty', 're_printing',
                                                       'cancel']).mapped(
                                'amount'))
                    jw_id = bz_lines.job_work_id.filtered(lambda jw: jw.product_id.id == pr.id)
                    if jw_id[0].incentive > 0.00:
                        fix_incentive += (jw_id[0].incentive * (pr.mrp_area * bz_lines.__len__()))
                        inc += (jw_id[0].incentive * (pr.mrp_area * bz_lines.__len__()))
                    amount_cr += (((bz_lines[0].job_work_id.area * bz_lines.__len__()) * bz_lines[
                        0].job_work_id.rate) + inc + ord_inc) - baz_pen
                    bazaar_rec[rec.reference + str(pr.id)] = {
                        'date': rec.date.strftime('%d/%m/%Y'), 'type': 'Receiving',
                        'doc': rec.reference, 'design': pr.name, 'size': bz_lines[0].barcode.size,
                        'rec_pcs': bz_lines.__len__(),
                        'rec_area': "{:.2f}".format(round(bz_lines[0].job_work_id.area * bz_lines.__len__(), 2)),
                        'rate': "{:.2f}".format(round(bz_lines[0].job_work_id.rate, 2)),
                        'inc': "{:.2f}".format(round(inc, 2)),
                        'bz_amount': "{:.2f}".format(
                            round((bz_lines[0].job_work_id.area * bz_lines.__len__()) * bz_lines[0].job_work_id.rate,
                                  2)),
                        'ord_inc': "{:.2f}".format(round(ord_inc, 2)), 'baz_pen': "{:.2f}".format(round(baz_pen, 2)),
                        'amount_cr': "{:.2f}".format(
                            round((((bz_lines[0].job_work_id.area * bz_lines.__len__()) * bz_lines[
                                0].job_work_id.rate) + inc + ord_inc) - baz_pen, 2)),
                        'bal': "{:.2f}".format(
                            round(balance + (((bz_lines[0].job_work_id.area * bz_lines.__len__()) * bz_lines[
                                0].job_work_id.rate) + inc + ord_inc) - baz_pen, 2))}
                    balance += (((bz_lines[0].job_work_id.area * bz_lines.__len__()) * bz_lines[
                        0].job_work_id.rate) + inc + ord_inc) - baz_pen
            bill = self.env['account.move'].search([('bazaar_id', '=', rec.id), ('state', '=', 'posted')], limit=1)
            account_payments = self.env['account.payment'].search(
                [('ref', '=', bill.name), ('payment_type', '=', 'outbound')])
            if account_payments:
                for rec in account_payments:
                    retention = abs(bill.line_ids.filtered(lambda lin: 'Retention Amount' in lin.name).price_unit)
                    tds = abs(bill.line_ids.filtered(lambda lin: 'TDS Deduction' in lin.name).price_unit)
                    bazaar_rec[bill.bazaar_id.reference + 'pmnt'] = {
                        'date': rec.date.strftime('%d/%m/%Y'), 'type': 'Payment',
                        'doc': f"{rec.name} ({bill.name})", 'amount_dr': "{:.2f}".format(round(rec.amount, 2)),
                        'gst_amount': bill.amount_tax,
                        'retention': retention,
                        'tds': "{:.2f}".format(round(tds, 2)),
                        'incentive': '',
                        'penality': '',
                        # 'bal': (balance + retention) - bill.amount_total
                        'bal': "{:.2f}".format(round(((balance+bill.amount_tax) - (rec.amount + tds)), 2))
                    }
                    # balance = (balance + retention) - bill.amount_total
                    balance = ((balance+bill.amount_tax) - (rec.amount +tds))
        total_rec_weight = 0.00
        totalstd_weight = 0.00
        total_area = 0.000
        total_loss = 0.00
        total_ttcloth = 0.00
        total_pcs = 0.00
        total_ttyarn = 0.00
        total_tttar = 0.00
        total_ttsilk = 0.00
        total_ttcotton_yarn = 0.00
        total_ttjute = 0.00
        total_ttother = 0.00
        if record:
            deliveries = self.env['stock.picking'].search([('main_jobwork_id', '=', record.id),
                                                           ('origin', '=', f"Main Job Work: {record.reference}")])
            returns = self.env['stock.picking'].search([('main_jobwork_id', '=', record.id),
                                                        ('origin', '=', f"Return/Main Job Work: {record.reference}")])
            iss_cloth = 0.00
            if deliveries:
                for rec in deliveries:
                    cloth = sum(rec.move_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'weaving_cloth').mapped(
                        'quantity_done'))
                    iss_cloth += cloth
                    yarn = sum(rec.move_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'yarn').mapped(
                        'quantity_done'))
                    silk = sum(rec.move_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'silk').mapped(
                        'quantity_done'))
                    tar = sum(rec.move_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'tar').mapped(
                        'quantity_done'))
                    cotton_yarn = sum(rec.move_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'cotton_cone').mapped(
                        'quantity_done'))
                    jute = sum(rec.move_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'jute_yarn').mapped(
                        'quantity_done'))
                    other = 0.00
                    if record.division_id.name == 'TUFTED':
                        if record.jobwork_line_ids.product_id.product_tmpl_id.construction[0].name != 'HAND LOOMED':
                            other = cloth
                    else:
                        # other = round(sum(rec.main_jobwork_id.alloted_material_ids.filtered(
                        #     lambda
                        #         mi: mi.product_id.product_tmpl_id.raw_material_group == 'other_raw_materials').mapped(
                        #     'alloted_quantity')), 3)
                        other = sum(rec.move_ids.filtered(
                            lambda
                                mi: mi.product_id.product_tmpl_id.raw_material_group == 'other_raw_materials').mapped(
                            'quantity_done'))
                    material_rec.append(
                        {'Date': rec.date_done.strftime('%d/%m/%Y') if rec.date_done else '', 'Type': 'Issue',
                         'Doc No': rec.name, 'Rec Weight': '', 'Loss': '',
                         'Cloth': "{:.3f}".format(round(cloth, 3)) if cloth > 0.00 else '-', 'Pcs': '',
                         'Area': '', 'Quality': '', 'Std. Rug weight': '',
                         'Yarn': "{:.3f}".format(round(yarn, 3)) if yarn > 0.00 else '-',
                         'Silk': "{:.3f}".format(round(silk, 3)) if silk > 0.00 else '-',
                         'Tar': "{:.3f}".format(round(tar, 3)) if tar > 0.00 else '-',
                         'Cotton Yarn': "{:.3f}".format(round(cotton_yarn, 3)) if cotton_yarn > 0.00 else '-',
                         'Jute': "{:.3f}".format(round(jute, 3)) if jute > 0.00 else '-',
                         'Other': "{:.3f}".format(round(other, 3)) if other > 0.00 else '-', 'Remark': ''})
            return_cloth = 0.00
            return_yarn = 0.00
            return_silk = 0.00
            return_tar = 0.00
            return_cotton_yarn = 0.00
            return_jute = 0.00
            return_other = 0.00
            if returns:
                for rec in returns:
                    cloth = round(sum(rec.move_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'weaving_cloth').mapped(
                        'quantity_done')), 3)
                    return_cloth += cloth
                    yarn = round(sum(rec.move_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'yarn').mapped(
                        'quantity_done')), 3)
                    return_yarn += yarn
                    silk = round(sum(rec.move_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'silk').mapped(
                        'quantity_done')), 3)
                    return_silk += silk
                    tar = round(sum(rec.move_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'tar').mapped(
                        'quantity_done')), 3)
                    return_tar += tar
                    cotton_yarn = round(sum(rec.move_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'cotton_cone').mapped(
                        'quantity_done')), 3)
                    return_cotton_yarn += cotton_yarn
                    jute = round(sum(rec.move_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'jute_yarn').mapped(
                        'quantity_done')), 3)
                    return_jute += jute
                    other = 0.00
                    if record.division_id.name == 'TUFTED':
                        if record.jobwork_line_ids.product_id.product_tmpl_id.construction[0].name != 'HAND LOOMED':
                            other = cloth
                    else:
                        other = round(sum(rec.move_ids.filtered(
                            lambda
                                mi: mi.product_id.product_tmpl_id.raw_material_group == 'other_raw_materials').mapped(
                            'quantity_done')), 3)
                    return_other += other
                    material_rec.append(
                        {'Date': rec.date_done.strftime('%d/%m/%Y') if rec.date_done else '', 'Type': 'Return',
                         'Doc No': rec.name, 'Rec Weight': '', 'Loss': '',
                         'Cloth': "{:.3f}".format(-cloth) if cloth > 0.00 else 0.000, 'Pcs': '',
                         'Area': '', 'Quality': '', 'Std. Rug weight': '',
                         'Yarn': "{:.3f}".format(-yarn) if yarn > 0.00 else 0.000,
                         'Silk': "{:.3f}".format(-silk) if silk > 0.00 else 0.000,
                         'Tar': "{:.3f}".format(-tar) if tar > 0.00 else 0.000,
                         'Cotton Yarn': "{:.3f}".format(-cotton_yarn) if cotton_yarn > 0.00 else 0.000,
                         'Jute': "{:.3f}".format(-jute) if jute > 0.00 else 0.000,
                         'Other': "{:.3f}".format(-other) if jute > 0.00 else 0.000, 'Remark': ''})
            total_iss_cloth = iss_cloth - round(return_cloth, 3)
            total_iss_yarn = round(sum(deliveries.move_ids.filtered(
                lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'yarn').mapped(
                'quantity_done')), 3) - round(return_yarn, 3)
            total_iss_silk = round(sum(deliveries.move_ids.filtered(
                lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'silk').mapped(
                'quantity_done')), 3) - round(return_silk, 3)
            total_iss_tar = round(sum(deliveries.move_ids.filtered(
                lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'tar').mapped(
                'quantity_done')), 3) - round(return_tar, 3)
            total_iss_cotton_yarn = round(sum(deliveries.move_ids.filtered(
                lambda
                    mi: mi.product_id.product_tmpl_id.raw_material_group == 'cotton_cone').mapped(
                'quantity_done')), 3) - round(return_cotton_yarn, 3)
            tptal_iss_jute = round(sum(deliveries.move_ids.filtered(
                lambda
                    mi: mi.product_id.product_tmpl_id.raw_material_group == 'jute_yarn').mapped(
                'quantity_done')), 3) - round(return_jute, 3)
            total_iss_other = 0.000
            if record.division_id.name == 'TUFTED':
                if record.jobwork_line_ids.product_id.product_tmpl_id.construction[0].name != 'HAND LOOMED':
                    total_iss_other = total_iss_cloth
            else:
                total_iss_other = round(sum(deliveries.move_ids.filtered(
                    lambda
                        mi: mi.product_id.product_tmpl_id.raw_material_group == 'other_raw_materials').mapped(
                    'quantity_done')), 3) - round(return_other, 3)
            total_ttcloth += total_iss_cloth
            total_ttyarn += total_iss_yarn
            total_tttar += total_iss_tar
            total_ttsilk += total_iss_silk
            total_ttcotton_yarn += total_iss_cotton_yarn
            total_ttjute += tptal_iss_jute
            total_ttother += total_iss_other

            issue = {'type': 'Issue', 'Cloth': "{:.3f}".format(total_iss_cloth),
                     'Yarn': "{:.3f}".format(total_iss_yarn), 'Silk': "{:.3f}".format(total_iss_silk),
                     'Tar': "{:.3f}".format(total_iss_tar),
                     'Cotton Yarn': "{:.3f}".format(total_iss_cotton_yarn),
                     'Jute': "{:.3f}".format(tptal_iss_jute), 'Other': "{:.3f}".format(total_iss_other)}
            material_summ_rec.append(issue)
            excess.append(issue)
            baazar_ids = record.baazar_lines_ids
            if baazar_ids:
                total_cloth = 0.0
                total_yarn = 0.0
                total_silk = 0.0
                total_tar = 0.0
                total_cotton_yarn = 0.0
                tptal_jute = 0.0
                total_other = 0.0
                #######################################
                total_std_cloth = 0.0
                total_std_cottonyarn = 0.0
                total_std_silk = 0.0
                total_std_tar = 0.0
                total_std_yarn = 0.0
                tptal_std_jute = 0.0
                total_std_other = 0.0
                for rec in baazar_ids:
                    # cloth = round(sum(rec.main_jobwork_id.alloted_material_ids.filtered(
                    #     lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'weaving_cloth').mapped(
                    #     'alloted_quantity')), 3)
                    area = sum([rec.product_id.mrp_area for rec in
                                rec.baazar_lines_ids.filtered(lambda bl: bl.state == 'verified')])
                    cloth = 0.000 if record.division_id.name == 'KELIM' else 0.00 if \
                    record.jobwork_line_ids.product_id.product_tmpl_id.construction[
                        0].name == 'HAND LOOMED' else round(area * 0.200, 4)
                    total_std_cloth = cloth
                    stand_weight = round(
                        (area * (record.jobwork_line_ids[0].product_id.product_tmpl_id.quality.weight + record.loss)),
                        2)
                    rug_weight = round(sum(rec.baazar_lines_ids.filtered(lambda bl: bl.state == 'verified').mapped(
                        'actual_weight')), 2)
                    total_rec_weight += rug_weight
                    totalstd_weight += stand_weight
                    total_area += area
                    yarn = round(sum(rec.main_jobwork_id.alloted_material_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'yarn').mapped(
                        'alloted_quantity')), 3)
                    total_std_yarn = yarn
                    silk = round(sum(rec.main_jobwork_id.alloted_material_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'silk').mapped(
                        'alloted_quantity')), 3)
                    total_std_silk = silk
                    tar = round(sum(rec.main_jobwork_id.alloted_material_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'tar').mapped(
                        'alloted_quantity')), 3)
                    total_std_tar = tar
                    cotton_yarn = round(sum(rec.main_jobwork_id.alloted_material_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'cotton_cone').mapped(
                        'alloted_quantity')), 3)
                    total_std_cottonyarn = cotton_yarn
                    jute = round(sum(rec.main_jobwork_id.alloted_material_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'jute_yarn').mapped(
                        'alloted_quantity')), 3)
                    tptal_std_jute = jute
                    other = 0.00
                    if record.division_id.name == 'TUFTED':
                        if record.jobwork_line_ids.product_id.product_tmpl_id.construction[0].name != 'HAND LOOMED':
                            other = cloth
                            total_std_other = round(sum(rec.main_jobwork_id.alloted_material_ids.filtered(
                                lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'weaving_cloth').mapped(
                                'alloted_quantity')), 3)
                    else:
                        other = round(sum(rec.main_jobwork_id.alloted_material_ids.filtered(
                            lambda
                                mi: mi.product_id.product_tmpl_id.raw_material_group == 'other_raw_materials').mapped(
                            'alloted_quantity')), 3)
                        total_std_other = other
                    loss = round(rec.main_jobwork_id.loss * area, 3),
                    total_weight = sum([rec.total_area for rec in record.jobwork_line_ids]) * record.jobwork_line_ids[
                        0].product_id.product_tmpl_id.quality.weight
                    lagat = rug_weight + loss[0] - cloth
                    if silk == 0.00 and tar == 0.00 and cotton_yarn == 0.00 and jute == 0.00 and other == 0.00:
                        yarn = rug_weight + float(loss[0]) - cloth
                    else:
                        yarn = (yarn / total_weight) * lagat
                    silk = (silk / total_weight) * lagat
                    tar = (tar / total_weight) * lagat
                    cotton_yarn = (cotton_yarn / total_weight) * lagat
                    jute = (jute / total_weight) * lagat
                    total_cloth += cloth
                    total_yarn += yarn
                    total_silk += silk
                    total_tar += tar
                    total_cotton_yarn += cotton_yarn
                    tptal_jute += jute
                    total_other += other
                    total_loss += loss[0]
                    total_ttcloth -= cloth
                    total_pcs += len(rec.baazar_lines_ids.filtered(lambda bl: bl.state == 'verified'))
                    total_ttyarn -= yarn
                    total_tttar -= tar
                    total_ttsilk -= silk
                    total_ttcotton_yarn -= cotton_yarn
                    total_ttjute -= jute
                    total_ttother -= other
                    material_rec.append(
                        {'Date': rec.date.strftime('%d/%m/%Y'), 'Type': 'Receive', 'Doc No': rec.reference,
                         'Rec Weight': "{:.3f}".format(round(rug_weight, 3)), 'Loss': "{:.3f}".format(float(loss[0])),
                         'Cloth': "{:.3f}".format(-round(cloth, 3)) if cloth > 0.00 else '-',
                         'Pcs': len(rec.baazar_lines_ids.filtered(lambda bl: bl.state == 'verified')),
                         'Area': "{:.3f}".format(round(area, 3)),
                         'Quality': rec.baazar_lines_ids.product_id[0].product_tmpl_id.quality.name,
                         'Std. Rug weight': "{:.3f}".format(round(stand_weight, 3)),
                         'Yarn': "{:.3f}".format(-round(yarn, 3)) if yarn > 0.00 else '-',
                         'Silk': "{:.3f}".format(-round(silk, 3)) if silk > 0.00 else '-',
                         'Tar': "{:.3f}".format(-round(tar, 3)) if tar > 0.00 else '-',
                         'Cotton Yarn': "{:.3f}".format(-round(cotton_yarn, 3)) if cotton_yarn > 0.00 else '-',
                         'Jute': "{:.3f}".format(-round(jute, 3)) if jute > 0.00 else '-',
                         'Other': "{:.3f}".format(-round(other, 3)) if other > 0.00 else '-', 'Remark': ''})
                consuption.append((
                    {'type': 'Standard', 'Cloth': "{:.3f}".format(round(total_std_cloth, 3)),
                     'Yarn': "{:.3f}".format(round(total_std_yarn, 3)),
                     'Silk': "{:.3f}".format(round(total_std_silk, 3)),
                     'Tar': "{:.3f}".format(round(total_std_tar, 3)),
                     'Cotton Yarn': "{:.3f}".format(round(total_std_cottonyarn, 3)),
                     'Jute': "{:.3f}".format(round(tptal_std_jute, 3)),
                     'Other': "{:.3f}".format(round(total_std_other, 3))}))
                material_summ_rec.append(
                    {'type': 'Receive',
                     'Cloth': "{:.3f}".format(-round(total_cloth, 3)) if total_cloth > 0.00 else "{:.3f}".format(0.000),
                     'Yarn': "{:.3f}".format(-round(total_yarn, 3)) if total_yarn > 0.00 else "{:.3f}".format(0.000),
                     'Silk': "{:.3f}".format(-round(total_silk, 3)) if total_silk > 0.00 else "{:.3f}".format(0.000),
                     'Tar': "{:.3f}".format(-round(total_tar, 3)) if total_tar > 0.00 else "{:.3f}".format(0.000),
                     'Cotton Yarn': "{:.3f}".format(
                         -round(total_cotton_yarn, 3)) if total_cotton_yarn > 0.00 else "{:.3f}".format(0.000),
                     'Jute': "{:.3f}".format(-round(tptal_jute, 3)) if tptal_jute > 0.00 else "{:.3f}".format(0.000),
                     'Other': "{:.3f}".format(-round(total_other, 3)) if total_other > 0.00 else "{:.3f}".format(
                         0.000)})
                consuption.append(
                    {'type': 'Actual', 'Cloth': "{:.3f}".format(round(total_cloth, 3)),
                     'Yarn': "{:.3f}".format(round(total_yarn, 3)),
                     'Silk': "{:.3f}".format(round(total_silk, 3)),
                     'Tar': "{:.3f}".format(round(total_tar, 3)),
                     'Cotton Yarn': "{:.3f}".format(round(total_cotton_yarn, 3)),
                     'Jute': "{:.3f}".format(round(tptal_jute, 3)),
                     'Other': "{:.3f}".format(round(total_other, 3))})
                consu = {'type': 'Consumption', 'Cloth': "{:.3f}".format(round(min(total_cloth, total_std_cloth), 3)),
                         'Yarn': "{:.3f}".format(round(min(total_yarn, total_std_yarn), 3)),
                         'Silk': "{:.3f}".format(round(min(total_silk, total_std_silk), 3)),
                         'Tar': "{:.3f}".format(round(min(total_tar, total_std_tar), 3)),
                         'Cotton Yarn': "{:.3f}".format(round(min(total_cotton_yarn, total_std_cottonyarn), 3)),
                         'Jute': "{:.3f}".format(round(min(tptal_jute, tptal_std_jute), 3)),
                         'Other': "{:.3f}".format(round(min(total_other, total_std_other), 3))}
                consuption.append(consu)
                excess.append(consu)
                excess.append(
                    {'type': 'Excess of Yarn',
                     'Cloth': "{:.3f}".format(round(total_iss_cloth - min(total_cloth, total_std_cloth), 3)),
                     'Yarn': "{:.3f}".format(round(total_iss_yarn - min(total_yarn, total_std_yarn), 3)),
                     'Silk': "{:.3f}".format(round(total_iss_silk - min(total_silk, total_std_silk), 3)),
                     'Tar': "{:.3f}".format(round(total_iss_tar - min(total_tar, total_std_tar), 3)),
                     'Cotton Yarn': "{:.3f}".format(
                         round(total_iss_cotton_yarn - min(total_cotton_yarn, total_std_cottonyarn), 3)),
                     'Jute': "{:.3f}".format(round(tptal_iss_jute - min(tptal_jute, tptal_std_jute), 3)),
                     'Other': "{:.3f}".format(round(total_iss_other - min(total_other, total_std_other), 3))})
            account_moves = self.env['account.move'].search([('job_work_id', '=', record.id)])
            if account_moves:
                total_amount = 0.00
                tds = 0.00
                for am in account_moves:
                    total_amount += am.amount_total
                    tds = -round(sum([rec.price_total for rec in am.invoice_line_ids.filtered(
                        lambda inl: 'TDS Deduction' in inl.name)]), 2)
                model_id = self.env.ref('innorug_manufacture.model_main_jobwork').id
                inno_inc_pen = self.env['inno.incentive.penalty'].search(
                    [('model_id', '=', model_id), ('rec_id', '=', record.id),
                     ('rec_id', '=', record.id)])
                rentention = round(sum(self.env['inno.incentive.penalty'].search(
                    [('partner_id', '=', record.subcontractor_id.id)]).filtered(
                    lambda iip: iip.type == 'retention' and record.reference in iip.remark).mapped('amount')), 3)
                account_summ_rec.append({'Weaving Invoice': "{:.2f}".format(amount_cr)})
                account_summ_rec.append({'Round Up': ''})
                account_summ_rec.append({'Round Down': ''})
                account_summ_rec.append({'Fix Incentive': "{:.2f}".format(fix_incentive, 3)})
                account_summ_rec.append({'Time Incentive': "{:.2f}".format(round(
                    sum(inno_inc_pen.filtered(lambda iip: iip.type == 'time_incentive').mapped('amount')), 3))})
                account_summ_rec.append({'Time Penality': "{:.2f}".format(round(
                    sum(inno_inc_pen.filtered(lambda iip: iip.type == 'time_penalty').mapped('amount')), 3))})
                account_summ_rec.append({'QC Penality': "{:.2f}".format(-round(
                    sum(inno_inc_pen.filtered(lambda iip: iip.type == 'qa_penalty').mapped('amount')), 3))})
                account_summ_rec.append({'Bazaar Limit Exceeded': "{:.2f}".format(-round(
                    sum(inno_inc_pen.filtered(lambda iip: iip.type == 'bazaar_penalty').mapped('amount')), 3))})
                account_summ_rec.append({'Barcode Re-Print': "{:.2f}".format(round(
                    sum(inno_inc_pen.filtered(lambda iip: iip.type == 're_printing').mapped('amount')), 3))})
                account_summ_rec.append({'Cancellation Penalty': "{:.2f}".format(round(
                    sum(inno_inc_pen.filtered(lambda iip: iip.type == 'cancel').mapped('amount')), 3))})
                account_summ_rec.append({'Retention': "{:.2f}".format(rentention)})
                account_summ_rec.append({'TDS': "{:.2f}".format(tds)})
                account_summ_rec.append({'Bazaar Incentive': "{:.2f}".format(round(
                    sum(inno_inc_pen.filtered(lambda iip: iip.type == 'incentive').mapped('amount')), 3))})
                account_summ_rec.append({'Weaving Payment': "{:.2f}".format(round(total_amount, 3))})

        data = {'subcontractor': {'name': record.subcontractor_id.name, 'address': record.subcontractor_id.street,
                                  'order_no': record.reference, 'city': record.subcontractor_id.city,
                                  'date': record.issue_date.strftime('%d/%m/%Y'),
                                  'contact_no': record.subcontractor_id.mobile or 'N/A',
                                  'due_date': record.expected_received_date.strftime('%d/%m/%Y'),
                                  'pan': record.subcontractor_id.pan_no or 'N/A', 'issue_by': self.env.user.name,
                                  'last_bazar': record.baazar_lines_ids[-1].date.strftime('%d/%m/%Y')
                                  if record.baazar_lines_ids else 'N/A', 'status': record.state,
                                  }, 'material_data': material_rec,
                'material_summ_rec': material_summ_rec, 'account_summ_rec': account_summ_rec, 'consuption': consuption,
                'excess': excess, 'sub_total': [{'total_rec_weight': "{:.3f}".format(round(total_rec_weight, 3)),
                                                 'totalstd_weight': "{:.3f}".format(round(totalstd_weight, 3)),
                                                 'total_area': "{:.3f}".format(round(total_area, 3)),
                                                 'total_loss': "{:.3f}".format(round(total_loss, 3)),
                                                 'total_cloth': "{:.3f}".format(round(total_ttcloth, 3)),
                                                 'total_pcs': total_pcs,
                                                 'total_yarn': "{:.3f}".format(round(total_ttyarn, 3)),
                                                 'total_tar': "{:.3f}".format(round(total_tttar, 3)),
                                                 'total_silk': "{:.3f}".format(round(total_ttsilk, 3)),
                                                 'total_cotton_yarn': "{:.3f}".format(round(total_ttcotton_yarn, 3)),
                                                 'total_jute': "{:.3f}".format(round(total_ttjute, 3)),
                                                 'total_other': "{:.3f}".format(round(total_ttother, 3))}],
                'bazaar_records': bazaar_rec.values()}
        return {
            'doc_ids': docids,
            'doc_model': 'main.baazar',
            'docs': record,
            'data': data,
            'company': company}



    @api.model
    def _get_report_values(self, docids, data=None):
        record = self.env['main.jobwork'].browse(docids)
        company = self.env['res.company'].search([], limit=1)
        bazaar_rec = dict()
        material_rec = []
        material_summ_rec = []
        account_summ_rec = []
        amount_cr = 0.0
        balance = 0.0
        consuption = []
        excess = []
        fix_incentive = 0.00

        for rec in record.baazar_lines_ids:
            for pr in rec.baazar_lines_ids.filtered(lambda bl: bl.state == 'verified').product_id:
                # for line in rec.baazar_lines_ids.filtered(lambda bl: bl.state == 'verified'):
                bz_lines = rec.baazar_lines_ids.filtered(
                    lambda bl: bl.state == 'verified' and pr.id in bl.product_id.ids)
                if bz_lines:
                    inc = 0.0
                    ord_inc = 0.0
                    baz_pen = 0.00
                    for br in bz_lines:
                        inc += sum(br.barcode.pen_inc_ids.filtered(lambda pl: pl.type == 'incentive').mapped('amount'))
                        ord_inc += sum(
                            br.barcode.pen_inc_ids.filtered(lambda pl: pl.type == 'time_incentive').mapped('amount'))
                        baz_pen += sum(
                            br.barcode.pen_inc_ids.filtered(
                                lambda pl: pl.type in ['time_penalty', 'bazaar_penalty', 'qa_penalty', 're_printing',
                                                       'cancel']).mapped(
                                'amount'))
                    jw_id = bz_lines.job_work_id.filtered(lambda jw: jw.product_id.id == pr.id)
                    if jw_id[0].incentive > 0.00:
                        fix_incentive += (jw_id[0].incentive * (pr.mrp_area * bz_lines.__len__()))
                        inc += (jw_id[0].incentive * (pr.mrp_area * bz_lines.__len__()))
                    amount_cr += (((bz_lines[0].job_work_id.area * bz_lines.__len__()) * bz_lines[
                        0].job_work_id.rate) + inc + ord_inc) - baz_pen
                    bazaar_rec[rec.reference + str(pr.id)] = {
                        'date': rec.date.strftime('%d/%m/%Y'), 'type': 'Receiving',
                        'doc': rec.reference, 'design': pr.name, 'size': bz_lines[0].barcode.size,
                        'rec_pcs': bz_lines.__len__(),
                        'rec_area': "{:.4f}".format(round(bz_lines[0].job_work_id.area * bz_lines.__len__(), 4)),
                        'rate': "{:.2f}".format(round(bz_lines[0].job_work_id.rate, 2)),
                        'inc': "{:.2f}".format(round(inc, 2)),
                        'bz_amount': "{:.2f}".format(
                            round((bz_lines[0].job_work_id.area * bz_lines.__len__()) * bz_lines[0].job_work_id.rate,
                                  2)),
                        'ord_inc': "{:.2f}".format(round(ord_inc, 2)), 'baz_pen': "{:.2f}".format(round(baz_pen, 2)),
                        'amount_cr': "{:.2f}".format(
                            round((((bz_lines[0].job_work_id.area * bz_lines.__len__()) * bz_lines[
                                0].job_work_id.rate) + inc + ord_inc) - baz_pen, 2)),
                        'bal': "{:.2f}".format(
                            round(balance + (((bz_lines[0].job_work_id.area * bz_lines.__len__()) * bz_lines[
                                0].job_work_id.rate) + inc + ord_inc) - baz_pen, 2))}
                    balance += (((bz_lines[0].job_work_id.area * bz_lines.__len__()) * bz_lines[
                        0].job_work_id.rate) + inc + ord_inc) - baz_pen
            bill = self.env['account.move'].search([('bazaar_id', '=', rec.id), ('state', '=', 'posted')], limit=1)
            account_payments = self.env['account.payment'].search(
                [('ref', '=', bill.name), ('payment_type', '=', 'outbound')])
            if account_payments:
                for rec in account_payments:
                    retention = abs(bill.line_ids.filtered(lambda lin: 'Retention Amount' in lin.name).price_unit)
                    tds = abs(bill.line_ids.filtered(lambda lin: 'TDS Deduction' in lin.name).price_unit)
                    bazaar_rec[bill.bazaar_id.reference + 'pmnt'] = {
                        'date': rec.date.strftime('%d/%m/%Y'), 'type': 'Payment',
                        'doc': f"{rec.name} ({bill.name})", 'amount_dr': "{:.2f}".format(round(rec.amount, 2)),
                        'gst_amount': bill.amount_tax,
                        'retention': retention,
                        'tds': "{:.2f}".format(round(tds, 2)),
                        'incentive': '',
                        'penality': '',
                        # 'bal': (balance + retention) - bill.amount_total
                        'bal': "{:.2f}".format(round(((balance+bill.amount_tax) - (rec.amount + tds)), 2))
                    }
                    # balance = (balance + retention) - bill.amount_total
                    balance = ((balance+bill.amount_tax) - (rec.amount +tds))
        total_rec_weight = 0.00
        totalstd_weight = 0.00
        total_area = 0.000
        total_loss = 0.00
        total_ttcloth = 0.00
        total_pcs = 0.00
        total_ttyarn = 0.00
        total_tttar = 0.00
        total_ttsilk = 0.00
        total_ttcotton_yarn = 0.00
        total_ttjute = 0.00
        total_ttother = 0.00
        if record:
            deliveries = self.env['stock.picking'].search([('main_jobwork_id', '=', record.id),
                                                           ('origin', '=', f"Main Job Work: {record.reference}")])
            returns = self.env['stock.picking'].search([('main_jobwork_id', '=', record.id),
                                                        ('origin', '=', f"Return/Main Job Work: {record.reference}")])
            iss_cloth = 0.00
            if deliveries:
                for rec in deliveries:
                    cloth = sum(rec.move_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'weaving_cloth').mapped(
                        'quantity_done'))
                    iss_cloth += cloth
                    yarn = sum(rec.move_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'yarn').mapped(
                        'quantity_done'))
                    silk = sum(rec.move_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'silk').mapped(
                        'quantity_done'))
                    tar = sum(rec.move_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'tar').mapped(
                        'quantity_done'))
                    cotton_yarn = sum(rec.move_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'cotton_cone').mapped(
                        'quantity_done'))
                    jute = sum(rec.move_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'jute_yarn').mapped(
                        'quantity_done'))
                    other = 0.00
                    if record.division_id.name == 'TUFTED':
                        if record.jobwork_line_ids.product_id.product_tmpl_id.construction[0].name != 'HAND LOOMED':
                            other = cloth
                    else:
                        # other = round(sum(rec.main_jobwork_id.alloted_material_ids.filtered(
                        #     lambda
                        #         mi: mi.product_id.product_tmpl_id.raw_material_group == 'other_raw_materials').mapped(
                        #     'alloted_quantity')), 3)
                        other = sum(rec.move_ids.filtered(
                            lambda
                                mi: mi.product_id.product_tmpl_id.raw_material_group == 'other_raw_materials').mapped(
                            'quantity_done'))
                        if record.division_id.name == 'KNOTTED':
                            other = sum(rec.move_ids.filtered(lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'tharri').mapped('quantity_done'))
                    material_rec.append(
                        {'Date': rec.date_done.strftime('%d/%m/%Y') if rec.date_done else '', 'Type': 'Issue',
                         'Doc No': rec.name, 'Rec Weight': '', 'Loss': '',
                         'Cloth': "{:.3f}".format(round(cloth, 3)) if cloth > 0.00 else '-', 'Pcs': '',
                         'Area': '', 'Quality': '', 'Std. Rug weight': '',
                         'Yarn': "{:.3f}".format(round(yarn, 3)) if yarn > 0.00 else '-',
                         'Silk': "{:.3f}".format(round(silk, 3)) if silk > 0.00 else '-',
                         'Tar': "{:.3f}".format(round(tar, 3)) if tar > 0.00 else '-',
                         'Cotton Yarn': "{:.3f}".format(round(cotton_yarn, 3)) if cotton_yarn > 0.00 else '-',
                         'Jute': "{:.3f}".format(round(jute, 3)) if jute > 0.00 else '-',
                         'Other': "{:.3f}".format(round(other, 3)) if other > 0.00 else '-', 'Remark': ''})
            return_cloth = 0.00
            return_yarn = 0.00
            return_silk = 0.00
            return_tar = 0.00
            return_cotton_yarn = 0.00
            return_jute = 0.00
            return_other = 0.00
            if returns:
                for rec in returns:
                    cloth = round(sum(rec.move_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'weaving_cloth').mapped(
                        'quantity_done')), 3)
                    return_cloth += cloth
                    yarn = round(sum(rec.move_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'yarn').mapped(
                        'quantity_done')), 3)
                    return_yarn += yarn
                    silk = round(sum(rec.move_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'silk').mapped(
                        'quantity_done')), 3)
                    return_silk += silk
                    tar = round(sum(rec.move_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'tar').mapped(
                        'quantity_done')), 3)
                    return_tar += tar
                    cotton_yarn = round(sum(rec.move_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'cotton_cone').mapped(
                        'quantity_done')), 3)
                    return_cotton_yarn += cotton_yarn
                    jute = round(sum(rec.move_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'jute_yarn').mapped(
                        'quantity_done')), 3)
                    return_jute += jute
                    other = 0.00
                    if record.division_id.name == 'TUFTED':
                        if record.jobwork_line_ids.product_id.product_tmpl_id.construction[0].name != 'HAND LOOMED':
                            other = cloth
                    else:
                        other = round(sum(rec.move_ids.filtered(
                            lambda
                                mi: mi.product_id.product_tmpl_id.raw_material_group == 'other_raw_materials').mapped(
                            'quantity_done')), 3)
                        if record.division_id.name == 'KNOTTED':
                            other = sum(rec.move_ids.filtered(
                                lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'tharri').mapped(
                                'quantity_done'))
                    return_other += other
                    material_rec.append(
                        {'Date': rec.date_done.strftime('%d/%m/%Y') if rec.date_done else '', 'Type': 'Return',
                         'Doc No': rec.name, 'Rec Weight': '', 'Loss': '',
                         'Cloth': "{:.3f}".format(-cloth) if cloth > 0.00 else 0.000, 'Pcs': '',
                         'Area': '', 'Quality': '', 'Std. Rug weight': '',
                         'Yarn': "{:.3f}".format(-yarn) if yarn > 0.00 else 0.000,
                         'Silk': "{:.3f}".format(-silk) if silk > 0.00 else 0.000,
                         'Tar': "{:.3f}".format(-tar) if tar > 0.00 else 0.000,
                         'Cotton Yarn': "{:.3f}".format(-cotton_yarn) if cotton_yarn > 0.00 else 0.000,
                         'Jute': "{:.3f}".format(-jute) if jute > 0.00 else 0.000,
                         'Other': "{:.3f}".format(-other) if jute > 0.00 else 0.000, 'Remark': ''})
            total_iss_cloth = iss_cloth - round(return_cloth, 3)
            total_iss_yarn = round(sum(deliveries.move_ids.filtered(
                lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'yarn').mapped(
                'quantity_done')), 3) - round(return_yarn, 3)
            total_iss_silk = round(sum(deliveries.move_ids.filtered(
                lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'silk').mapped(
                'quantity_done')), 3) - round(return_silk, 3)
            total_iss_tar = round(sum(deliveries.move_ids.filtered(
                lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'tar').mapped(
                'quantity_done')), 3) - round(return_tar, 3)
            total_iss_cotton_yarn = round(sum(deliveries.move_ids.filtered(
                lambda
                    mi: mi.product_id.product_tmpl_id.raw_material_group == 'cotton_cone').mapped(
                'quantity_done')), 3) - round(return_cotton_yarn, 3)
            tptal_iss_jute = round(sum(deliveries.move_ids.filtered(
                lambda
                    mi: mi.product_id.product_tmpl_id.raw_material_group == 'jute_yarn').mapped(
                'quantity_done')), 3) - round(return_jute, 3)
            total_iss_other = 0.000
            if record.division_id.name == 'TUFTED':
                if record.jobwork_line_ids.product_id.product_tmpl_id.construction[0].name != 'HAND LOOMED':
                    total_iss_other = total_iss_cloth
            else:
                total_iss_other = round(sum(deliveries.move_ids.filtered(
                    lambda
                        mi: mi.product_id.product_tmpl_id.raw_material_group == 'other_raw_materials').mapped(
                    'quantity_done')), 3) - round(return_other, 3)
                if record.division_id.name == 'KNOTTED':
                    total_iss_other = round(sum(deliveries.move_ids.filtered(
                        lambda
                            mi: mi.product_id.product_tmpl_id.raw_material_group == 'tharri').mapped(
                        'quantity_done')), 3) - round(return_other, 3)
            total_ttcloth += total_iss_cloth
            total_ttyarn += total_iss_yarn
            total_tttar += total_iss_tar
            total_ttsilk += total_iss_silk
            total_ttcotton_yarn += total_iss_cotton_yarn
            total_ttjute += tptal_iss_jute
            total_ttother += total_iss_other

            issue = {'type': 'Issue', 'Cloth': "{:.3f}".format(total_iss_cloth),
                     'Yarn': "{:.3f}".format(total_iss_yarn), 'Silk': "{:.3f}".format(total_iss_silk),
                     'Tar': "{:.3f}".format(total_iss_tar),
                     'Cotton Yarn': "{:.3f}".format(total_iss_cotton_yarn),
                     'Jute': "{:.3f}".format(tptal_iss_jute), 'Other': "{:.3f}".format(total_iss_other)}
            material_summ_rec.append(issue)
            excess.append(issue)
            baazar_ids = record.baazar_lines_ids
            if baazar_ids:
                total_cloth = 0.0
                total_yarn = 0.0
                total_silk = 0.0
                total_tar = 0.0
                total_cotton_yarn = 0.0
                tptal_jute = 0.0
                total_other = 0.0
                #######################################
                total_std_cloth = 0.0
                total_std_cottonyarn = 0.0
                total_std_silk = 0.0
                total_std_tar = 0.0
                total_std_yarn = 0.0
                tptal_std_jute = 0.0
                total_std_other = 0.0
                for rec in baazar_ids:
                    # cloth = round(sum(rec.main_jobwork_id.alloted_material_ids.filtered(
                    #     lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'weaving_cloth').mapped(
                    #     'alloted_quantity')), 3)
                    area = sum([rec.product_id.mrp_area for rec in
                                rec.baazar_lines_ids.filtered(lambda bl: bl.state == 'verified')])
                    cloth = 0.000 if record.division_id.name in ['KELIM','KNOTTED'] else 0.00 if \
                    record.jobwork_line_ids.product_id.product_tmpl_id.construction[
                        0].name == 'HAND LOOMED' else round(area * 0.200, 4)
                    total_std_cloth = cloth
                    stand_weight = round(
                        (area * (record.jobwork_line_ids[0].product_id.product_tmpl_id.quality.weight + record.loss)),
                        2)
                    rug_weight = round(sum(rec.baazar_lines_ids.filtered(lambda bl: bl.state == 'verified').mapped(
                        'actual_weight')), 2)
                    total_rec_weight += rug_weight
                    totalstd_weight += stand_weight
                    total_area += area
                    yarn = round(sum(rec.main_jobwork_id.alloted_material_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'yarn').mapped(
                        'alloted_quantity')), 3)
                    total_std_yarn = yarn
                    silk = round(sum(rec.main_jobwork_id.alloted_material_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'silk').mapped(
                        'alloted_quantity')), 3)
                    total_std_silk = silk
                    tar = round(sum(rec.main_jobwork_id.alloted_material_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'tar').mapped(
                        'alloted_quantity')), 3)
                    total_std_tar = tar
                    cotton_yarn = round(sum(rec.main_jobwork_id.alloted_material_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'cotton_cone').mapped(
                        'alloted_quantity')), 3)
                    total_std_cottonyarn = cotton_yarn
                    jute = round(sum(rec.main_jobwork_id.alloted_material_ids.filtered(
                        lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'jute_yarn').mapped(
                        'alloted_quantity')), 3)
                    tptal_std_jute = jute
                    other = 0.00
                    if record.division_id.name == 'TUFTED':
                        if record.jobwork_line_ids.product_id.product_tmpl_id.construction[0].name != 'HAND LOOMED':
                            other = cloth
                            total_std_other = round(sum(rec.main_jobwork_id.alloted_material_ids.filtered(
                                lambda mi: mi.product_id.product_tmpl_id.raw_material_group == 'weaving_cloth').mapped(
                                'alloted_quantity')), 3)
                    else:
                        other = round(sum(rec.main_jobwork_id.alloted_material_ids.filtered(
                            lambda
                                mi: mi.product_id.product_tmpl_id.raw_material_group == 'other_raw_materials').mapped(
                            'alloted_quantity')), 3)
                        if record.division_id.name == 'KNOTTED':
                            other = round(sum(rec.main_jobwork_id.alloted_material_ids.filtered(
                                lambda
                                    mi: mi.product_id.product_tmpl_id.raw_material_group == 'tharri').mapped(
                                'alloted_quantity')), 3)
                        total_std_other = other
                    loss = round(rec.main_jobwork_id.loss * area, 3),
                    total_weight = round(sum(record.alloted_material_ids.mapped('alloted_quantity')),3) if record.division_id.name in ['KELIM','KNOTTED'] else sum([rec.total_area for rec in record.jobwork_line_ids]) * record.jobwork_line_ids[
                        0].product_id.product_tmpl_id.quality.weight
                    lagat = rug_weight + loss[0] - cloth
                    if silk == 0.00 and tar == 0.00 and cotton_yarn == 0.00 and jute == 0.00 and other == 0.00:
                        yarn = rug_weight + float(loss[0]) - cloth
                    else:
                        yarn = (yarn / total_weight) * lagat
                    silk = (silk / total_weight) * lagat
                    tar = (tar / total_weight) * lagat
                    cotton_yarn = (cotton_yarn / total_weight) * lagat
                    jute = (jute / total_weight) * lagat
                    total_cloth += cloth
                    total_yarn += yarn
                    total_silk += silk
                    total_tar += tar
                    total_cotton_yarn += cotton_yarn
                    tptal_jute += jute
                    total_other += other
                    total_loss += loss[0]
                    total_ttcloth -= cloth
                    total_pcs += len(rec.baazar_lines_ids.filtered(lambda bl: bl.state == 'verified'))
                    total_ttyarn -= yarn
                    total_tttar -= tar
                    total_ttsilk -= silk
                    total_ttcotton_yarn -= cotton_yarn
                    total_ttjute -= jute
                    total_ttother -= other
                    material_rec.append(
                        {'Date': rec.date.strftime('%d/%m/%Y'), 'Type': 'Receive', 'Doc No': rec.reference,
                         'Rec Weight': "{:.3f}".format(round(rug_weight, 3)), 'Loss': "{:.3f}".format(float(loss[0])),
                         'Cloth': "{:.3f}".format(-round(cloth, 3)) if cloth > 0.00 else '-',
                         'Pcs': len(rec.baazar_lines_ids.filtered(lambda bl: bl.state == 'verified')),
                         'Area': "{:.3f}".format(round(area, 3)),
                         'Quality': rec.baazar_lines_ids.product_id[0].product_tmpl_id.quality.name,
                         'Std. Rug weight': "{:.3f}".format(round(stand_weight, 3)),
                         'Yarn': "{:.3f}".format(-round(yarn, 3)) if yarn > 0.00 else '-',
                         'Silk': "{:.3f}".format(-round(silk, 3)) if silk > 0.00 else '-',
                         'Tar': "{:.3f}".format(-round(tar, 3)) if tar > 0.00 else '-',
                         'Cotton Yarn': "{:.3f}".format(-round(cotton_yarn, 3)) if cotton_yarn > 0.00 else '-',
                         'Jute': "{:.3f}".format(-round(jute, 3)) if jute > 0.00 else '-',
                         'Other': "{:.3f}".format(-round(other, 3)) if other > 0.00 else '-', 'Remark': ''})
                consuption.append((
                    {'type': 'Standard', 'Cloth': "{:.3f}".format(round(total_std_cloth, 3)),
                     'Yarn': "{:.3f}".format(round(total_std_yarn, 3)),
                     'Silk': "{:.3f}".format(round(total_std_silk, 3)),
                     'Tar': "{:.3f}".format(round(total_std_tar, 3)),
                     'Cotton Yarn': "{:.3f}".format(round(total_std_cottonyarn, 3)),
                     'Jute': "{:.3f}".format(round(tptal_std_jute, 3)),
                     'Other': "{:.3f}".format(round(total_std_other, 3))}))
                material_summ_rec.append(
                    {'type': 'Receive',
                     'Cloth': "{:.3f}".format(-round(total_cloth, 3)) if total_cloth > 0.00 else "{:.3f}".format(0.000),
                     'Yarn': "{:.3f}".format(-round(total_yarn, 3)) if total_yarn > 0.00 else "{:.3f}".format(0.000),
                     'Silk': "{:.3f}".format(-round(total_silk, 3)) if total_silk > 0.00 else "{:.3f}".format(0.000),
                     'Tar': "{:.3f}".format(-round(total_tar, 3)) if total_tar > 0.00 else "{:.3f}".format(0.000),
                     'Cotton Yarn': "{:.3f}".format(
                         -round(total_cotton_yarn, 3)) if total_cotton_yarn > 0.00 else "{:.3f}".format(0.000),
                     'Jute': "{:.3f}".format(-round(tptal_jute, 3)) if tptal_jute > 0.00 else "{:.3f}".format(0.000),
                     'Other': "{:.3f}".format(-round(total_other, 3)) if total_other > 0.00 else "{:.3f}".format(
                         0.000)})
                consuption.append(
                    {'type': 'Actual', 'Cloth': "{:.3f}".format(round(total_cloth, 3)),
                     'Yarn': "{:.3f}".format(round(total_yarn, 3)),
                     'Silk': "{:.3f}".format(round(total_silk, 3)),
                     'Tar': "{:.3f}".format(round(total_tar, 3)),
                     'Cotton Yarn': "{:.3f}".format(round(total_cotton_yarn, 3)),
                     'Jute': "{:.3f}".format(round(tptal_jute, 3)),
                     'Other': "{:.3f}".format(round(total_other, 3))})
                consu = {'type': 'Consumption', 'Cloth': "{:.3f}".format(round(min(total_cloth, total_std_cloth), 3)),
                         'Yarn': "{:.3f}".format(round(min(total_yarn, total_std_yarn), 3)),
                         'Silk': "{:.3f}".format(round(min(total_silk, total_std_silk), 3)),
                         'Tar': "{:.3f}".format(round(min(total_tar, total_std_tar), 3)),
                         'Cotton Yarn': "{:.3f}".format(round(min(total_cotton_yarn, total_std_cottonyarn), 3)),
                         'Jute': "{:.3f}".format(round(min(tptal_jute, tptal_std_jute), 3)),
                         'Other': "{:.3f}".format(round(min(total_other, total_std_other), 3))}
                consuption.append(consu)
                excess.append(consu)
                excess.append(
                    {'type': 'Excess of Yarn',
                     'Cloth': "{:.3f}".format(round(total_iss_cloth - min(total_cloth, total_std_cloth), 3)),
                     'Yarn': "{:.3f}".format(round(total_iss_yarn - min(total_yarn, total_std_yarn), 3)),
                     'Silk': "{:.3f}".format(round(total_iss_silk - min(total_silk, total_std_silk), 3)),
                     'Tar': "{:.3f}".format(round(total_iss_tar - min(total_tar, total_std_tar), 3)),
                     'Cotton Yarn': "{:.3f}".format(
                         round(total_iss_cotton_yarn - min(total_cotton_yarn, total_std_cottonyarn), 3)),
                     'Jute': "{:.3f}".format(round(tptal_iss_jute - min(tptal_jute, tptal_std_jute), 3)),
                     'Other': "{:.3f}".format(round(total_iss_other - min(total_other, total_std_other), 3))})
            account_moves = self.env['account.move'].search([('job_work_id', '=', record.id)])
            if account_moves:
                total_amount = 0.00
                tds = 0.00
                for am in account_moves:
                    total_amount += am.amount_total
                    tds += round(sum([rec.price_total for rec in am.invoice_line_ids.filtered(
                        lambda inl: 'TDS Deduction' in inl.name)]), 2)
                model_id = self.env.ref('innorug_manufacture.model_main_jobwork').id
                inno_inc_pen = self.env['inno.incentive.penalty'].search(
                    [('model_id', '=', model_id), ('rec_id', '=', record.id),
                     ('rec_id', '=', record.id)])
                rentention = round(sum(self.env['inno.incentive.penalty'].search(
                    [('partner_id', '=', record.subcontractor_id.id)]).filtered(
                    lambda iip: iip.type == 'retention' and record.reference in iip.remark).mapped('amount')), 3)
                import math
                round_amount = rentention % 1
                rounded_down = 0.00
                rounded_up = 0.00
                up = 0.00
                down = 0.00
                if round_amount > 0 and round_amount < 0.50:
                    # bill.write({'invoice_cash_rounding_id': dowm_round_off.id})
                    down = round_amount
                    rounded_down = math.floor(rentention)
                elif round_amount > 0:
                    rounded_up = math.ceil(rentention)
                    up = round_amount
                    # bill.write({'invoice_cash_rounding_id': up_round_off.id})
                account_summ_rec.append({'Weaving Invoice': "{:.2f}".format(amount_cr)})
                account_summ_rec.append({'Round Up': "{:.2f}".format(up, 3)})
                account_summ_rec.append({'Round Down': "{:.2f}".format(down, 3)})
                account_summ_rec.append({'Fix Incentive': "{:.2f}".format(fix_incentive, 3)})
                account_summ_rec.append({'Time Incentive': "{:.2f}".format(round(
                    sum(inno_inc_pen.filtered(lambda iip: iip.type == 'time_incentive').mapped('amount')), 3))})
                account_summ_rec.append({'Time Penality': "{:.2f}".format(round(
                    sum(inno_inc_pen.filtered(lambda iip: iip.type == 'time_penalty').mapped('amount')), 3))})
                account_summ_rec.append({'QC Penality': "{:.2f}".format(-round(
                    sum(inno_inc_pen.filtered(lambda iip: iip.type == 'qa_penalty').mapped('amount')), 3))})
                account_summ_rec.append({'Bazaar Limit Exceeded': "{:.2f}".format(-round(
                    sum(inno_inc_pen.filtered(lambda iip: iip.type == 'bazaar_penalty').mapped('amount')), 3))})
                account_summ_rec.append({'Barcode Re-Print': "{:.2f}".format(round(
                    sum(inno_inc_pen.filtered(lambda iip: iip.type == 're_printing').mapped('amount')), 3))})
                account_summ_rec.append({'Cancellation Penalty': "{:.2f}".format(round(
                    sum(inno_inc_pen.filtered(lambda iip: iip.type == 'cancel').mapped('amount')), 3))})
                # account_summ_rec.append({'Retention': "{:.2f}".format(rentention)})
                account_summ_rec.append({'Bazaar Incentive': "{:.2f}".format(round(
                    sum(inno_inc_pen.filtered(lambda iip: iip.type == 'incentive').mapped('amount')), 3))})
                account_summ_rec.append({'TDS': "{:.2f}".format(-tds)})
                account_summ_rec.append({'Weaving Payment': "{:.2f}".format(round(total_amount, 3))})
                account_summ_rec.append({'Retention': "{:.2f}".format(rounded_up if rounded_up > 0.00 else rounded_down)})

        data = {'subcontractor': {'name': record.subcontractor_id.name, 'address': record.subcontractor_id.street,
                                  'order_no': record.reference, 'city': record.subcontractor_id.city,
                                  'date': record.issue_date.strftime('%d/%m/%Y'),
                                  'contact_no': record.subcontractor_id.mobile or 'N/A',
                                  'due_date': record.expected_received_date.strftime('%d/%m/%Y'),
                                  'pan': record.subcontractor_id.pan_no or 'N/A', 'issue_by': self.env.user.name,
                                  'last_bazar': record.baazar_lines_ids[-1].date.strftime('%d/%m/%Y')
                                  if record.baazar_lines_ids else 'N/A', 'status': record.state,
                                  }, 'material_data': material_rec,
                'material_summ_rec': material_summ_rec, 'account_summ_rec': account_summ_rec, 'consuption': consuption,
                'excess': excess, 'sub_total': [{'total_rec_weight': "{:.3f}".format(round(total_rec_weight, 3)),
                                                 'totalstd_weight': "{:.3f}".format(round(totalstd_weight, 3)),
                                                 'total_area': "{:.3f}".format(round(total_area, 3)),
                                                 'total_loss': "{:.3f}".format(round(total_loss, 3)),
                                                 'total_cloth': "{:.3f}".format(round(total_ttcloth, 3)),
                                                 'total_pcs': total_pcs,
                                                 'total_yarn': "{:.3f}".format(round(total_ttyarn, 3)),
                                                 'total_tar': "{:.3f}".format(round(total_tttar, 3)),
                                                 'total_silk': "{:.3f}".format(round(total_ttsilk, 3)),
                                                 'total_cotton_yarn': "{:.3f}".format(round(total_ttcotton_yarn, 3)),
                                                 'total_jute': "{:.3f}".format(round(total_ttjute, 3)),
                                                 'total_other': "{:.3f}".format(round(total_ttother, 3))}],
                'rug_omt_total': [{'pcs': "{:.0f}".format(round(sum([float(rec.get('rec_pcs')) for rec in bazaar_rec.values() if rec.get('rec_pcs')]), 3)),
                               'area': "{:.4f}".format(round(sum([float(rec.get('rec_area')) for rec in bazaar_rec.values() if rec.get('rec_area')]), 4)),
                               'inc': "{:.2f}".format(round(sum([float(rec.get('inc')) for rec in bazaar_rec.values() if rec.get('inc')]), 3)),
                               'bzzamunt': "{:.2f}".format(round(sum([float(rec.get('bz_amount')) for rec in bazaar_rec.values() if rec.get('bz_amount')]), 3)),
                               'other_inc': "{:.2f}".format(round(sum([float(rec.get('ord_inc')) for rec in bazaar_rec.values() if rec.get('ord_inc')]), 3)),
                               'penality':  "{:.2f}".format(round(sum([float(rec.get('penality')) for rec in bazaar_rec.values() if rec.get('penality')]), 3)),
                               'gst_amt': "{:.2f}".format(round(sum([float(rec.get('gst_amount')) for rec in bazaar_rec.values() if rec.get('gst_amount')]), 3)),
                               'tds': "{:.2f}".format(round(sum([float(rec.get('tds')) for rec in bazaar_rec.values() if rec.get('tds')]), 3)),
                               'amt_dr': "{:.2f}".format(round(sum([float(rec.get('amount_dr')) for rec in bazaar_rec.values() if rec.get('amount_dr')]), 3)),
                               'amt_cr': "{:.2f}".format(round(sum([float(rec.get('amount_cr')) for rec in bazaar_rec.values() if rec.get('amount_cr')]), 3)),
                               'bal': "{:.2f}".format(round(balance, 3)),
                               }],
                'thari' : 'yes' if record.division_id.name == 'KNOTTED'else 'no',
                'bazaar_records': bazaar_rec.values()}
        return {
            'doc_ids': docids,
            'doc_model': 'main.baazar',
            'docs': record,
            'data': data,
            'company': company}

