/** @odoo-module */

import { registry } from "@web/core/registry"
import { KpiCard } from './kpi_card/kpi_card'
import { ChartRenderer } from "./chart_renderer/chart_renderer"
import {loadJS} from '@web/core/assets'
import { useService } from "@web/core/utils/hooks"
const { Component, onWillStart, useRef, onMounted, useState } = owl
import { getColor } from "@web/views/graph/colors"
import { browser } from "@web/core/browser/browser"
import { routeToUrl } from "@web/core/browser/router_service"

export class OwlWeavingDashboard extends Component {

    //top products
        async getTopProducts() {
            let domain = []
            if (this.state.period > 0){
                domain.push(['create_date', '>' , this.state.current_date])
            }
            const data = await this.orm.readGroup('mrp.production', domain, ['product_id', 'product_qty'], ['product_id'], { limit:5, orderby: "product_qty desc"})

            this.state.topProducts = {
                data: {
                labels: data.map(d=>d.product_id[1] ? d.product_id[1].concat(' [ID] : ', d.product_id[0]): 'N/A'),
                  datasets: [
                  {
                    label: 'Quantity Ordered',
                    data: data.map(d=>d.product_qty),
                    hoverOffset: 10,
                    backgroundColor: data.map((_, index) => getColor(index+7)),
                  }]
              },
              domain,
              label_id: true,
              model: 'mrp.production',
              field_check: 'product_id'
            }
        }

    //top job workers
    async getTopJobWorkers() {
            let domain = []
            if (this.state.period > 0){
                domain.push(['issue_date', '>' , this.state.current_date])
            }
            else {
                domain.push(['issue_date', '=' , this.state.current_date])
            }
            const data = await this.orm.readGroup('mrp.job.work', domain, ['subcontractor_id', 'received_qty:sum'], ['subcontractor_id'], { limit:5, orderby: "received_qty desc"})
            this.state.topJobWorkers = {
                data: {
                labels: data.map(d=>d.subcontractor_id[1] ? d.subcontractor_id[1].concat(' [Code] : ', d.subcontractor_id[0]) : 'N/A'),
                  datasets: [
                  {
                    label: 'Received Weaved Products',
                    data: data.map(d=>d.received_qty),
                    hoverOffset: 10,
                    backgroundColor: data.map((_, index) => getColor(index+16)),
                  }]
              },
              label_id: true,
              model: 'res.partner',
              field_check: 'id'
            }
        }

    //Job work report
    async getJobWorkReport() {
            let domain = []
            if (this.state.period > 0){
                domain.push(['issue_date', '>' , this.state.current_date])
            }

            const data = await this.orm.readGroup('main.jobwork', domain, ['issue_date', 'remaining_days'], ['issue_date', 'remaining_days'], {orderby: "issue_date", lazy:false})
            const onTimeJw = data.filter(d=>d.remaining_days >= 0)
            const lateJw = data.filter(d=>d.remaining_days < 0)

            const labels = [... new Set(data.map(d=>d.issue_date))]

            this.state.jobWorkReport = {
                data: {
                labels: labels,
                  datasets: [
                  {
                    label: 'On Time',
                    data: labels.map(l=>onTimeJw.filter(otj=>l == otj.issue_date).map(j=>j.__count).reduce((a,c)=>a+c, 0)),
                    hoverOffset: 4,
                    backgroundColor: 'green',
                  },
                  {
                    label: 'Late',
                    data: labels.map(l=>lateJw.filter(otj=>l == otj.issue_date).map(j=>j.__count).reduce((a,c)=>a+c, 0)),
                    hoverOffset: 4,
                    backgroundColor: 'red',
                  }]
              },
              domain: [['issue_date', '>' , this.state.current_date]],
              model: 'main.jobwork',
              field_check: 'issue_date'
            }
        }

    //Division wise Report
    async getDivisionWiseReport() {
           let domain = []
            if (this.state.period > 0){
                domain.push(['issue_date', '>' , this.state.current_date])
            }

            const data = await this.orm.readGroup('main.jobwork', domain, ['issue_date', 'division_id'], ['issue_date', 'division_id'], {orderby: "issue_date", lazy:false})
            const labels = [... new Set(data.map(d=>d.issue_date))]
            const division_label = [... new Set(data.map(d=>d.division_id[1]))]
            let act_data = []
            for (let val in division_label) {
                act_data.push(
                {
                    label: division_label[val],
                    data: labels.map(l=>data.filter(otj=>l == otj.issue_date && otj.division_id[1] == division_label[val]).map(j=>j.__count).reduce((a,c)=>a+c, 0)),
                    hoverOffset: 4,
                    backgroundColor: getColor(val)
                })
            }

            this.state.divisionWiseReport = {
                data: {
                labels: labels,
                  datasets: act_data
              },
              domain: [['issue_date', '>' , this.state.current_date]],
              check_label: true,
              model: 'main.jobwork',
              field_check: 'issue_date'
            }
        }

    setup(){
        this.cookieServie = useService("cookie")
        if (this.cookieServie.current.weaving_option_selected == undefined) {
            this.cookieServie.setCookie('weaving_option_selected', 7)
        }

        this.state = useState({
            jobIssue: {
                value:20,
                percentage:7,
                lateValue: 10,
                latePercentage: 10
            },
            product: {
                value:20,
                percentage:7,
            },
            expense: {
                value:20,
                percentage:7,
            },
            period: this.cookieServie.current.weaving_option_selected,
        })
        this.orm = useService("orm")
        this.actionService = useService("action")

        const old_chartJs = document.querySelector('script[src="/web/static/lib/Chart/Chart.js"]')
        let router = useService("router")

        if (old_chartJs) {
            this.doWeavingAction(router, old_chartJs)
        }

        onWillStart(async ()=>{
            this.getDates()
            await this.getJobWorkIssue()
            await this.getProductReceived()
            await this.getExpense()

            await this.getTopProducts()
            await this.getTopJobWorkers()
            await this.getJobWorkReport()
            await this.getDivisionWiseReport()
        })
    }

    async doWeavingAction(router, old_chartJs) {
        let domain = [['name', '=', 'Weaving Dashboard']]
        const data = await this.orm.readGroup('ir.actions.actions', domain, ['id'], [])

        let { search, hash} = router.current
        search.old_chartJs = old_chartJs != null ? "0" : "1"
        hash.action = data[0].id
        browser.location.href = browser.location.origin + routeToUrl(router.current)
    }

    async onChangePeriod(){
        this.cookieServie.setCookie('weaving_option_selected', this.state.period)
        this.getDates()
        await this.getJobWorkIssue()
        await this.getProductReceived()
        await this.getExpense()

        await this.getTopProducts()
        await this.getTopJobWorkers()
        await this.getJobWorkReport()
        await this.getDivisionWiseReport()
    }

    getDates(){
        this.state.current_date = moment().subtract(this.state.period, 'days').format('DD/MM/YYYY')
        this.state.previous_date = moment().subtract(this.state.period * 2, 'days').format('DD/MM/YYYY')
    }


    async getJobWorkIssue(){
//    in progress
        let domain = []
        if (this.state.period > 0){
            domain.push(['issue_date','>', this.state.current_date])
        }
        const data = await this.orm.searchCount("main.jobwork", domain)
        this.state.jobIssue.value = data

//         previous period
        let prev_domain = []
        if (this.state.period > 0){
            prev_domain.push(['issue_date','>', this.state.previous_date], ['issue_date','<=', this.state.current_date])
        }
        const prev_issue_data = await this.orm.searchCount("main.jobwork", prev_domain)
        const percentage = ((data - prev_issue_data)/prev_issue_data) * 100
        this.state.jobIssue.percentage = percentage.toFixed(2)

//        late
        domain.push(['remaining_days', '<', 0])
        const lateData = await this.orm.searchCount("main.jobwork", domain)
        this.state.jobIssue.lateValue = lateData

//        previous late
        prev_domain.push(['remaining_days', '<', 0])
        const prev_late_issue_data = await this.orm.searchCount("main.jobwork", prev_domain)
        const latePercentage = ((data - prev_late_issue_data)/prev_late_issue_data) * 100
        this.state.jobIssue.latePercentage = latePercentage.toFixed(2)

    }

    async getProductReceived(){
        let domain = [['state', '=', 'verified']]
        if (this.state.period > 0){
            domain.push(['date', '>', this.state.current_date])
        }
        const data = await this.orm.searchCount("mrp.baazar.product.lines", domain)
        this.state.product.value = data

//         previous period
        let prev_domain = [['state', '=', 'verified']]
        if (this.state.period > 0){
            prev_domain.push(['date','>', this.state.previous_date], ['date','<=', this.state.current_date])
        }
        const prev_data = await this.orm.searchCount("account.move", prev_domain)
        const percentage = ((data - prev_data)/prev_data) * 100
        this.state.product.percentage = percentage.toFixed(2)

    }

    async getExpense(){
        let domain = [['state', '=', 'posted'], ['bazaar_id', '!=', false]]
        if (this.state.period > 0){
            domain.push(['date', '>', this.state.current_date])
        }
        const data = await this.orm.readGroup("account.move", domain, ['amount_total:sum'], [])
        this.state.expense.value = `₹ ${(data[0].amount_total/1000).toFixed(2)}K`

//         previous period
        let prev_domain = [['state', '=', 'posted'], ['bazaar_id', '!=', false]]
        if (this.state.period > 0){
            prev_domain.push(['date','>', this.state.previous_date], ['date','<=', this.state.current_date])
        }
        const prev_data = await this.orm.readGroup("account.move", prev_domain, ['amount_total:sum'], [])
        const percentage = ((data[0].amount_total - prev_data[0].amount_total)/prev_data[0].amount_total) * 100
        this.state.expense.percentage = percentage.toFixed(2)

    }


    async viewJobWorks(){
        let domain = []
        if (this.state.period > 0){
            domain.push(['issue_date','>', this.state.current_date])
        }
        const data = await this.orm.searchCount("main.jobwork", domain)

        if (data > 0) {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                name: "Job Works (In Progress)",
                res_model: "main.jobwork",
                domain,
                views: [
                    [false, "list"],
                    [false, "form"],
                ]
            })
        }
    }

    async viewLateJobWorks(){
        let domain = [['remaining_days', '<', 0]]
        if (this.state.period > 0){
            domain.push(['issue_date','>', this.state.current_date])
        }

        const lateData = await this.orm.searchCount("main.jobwork", domain)

        if (lateData > 0) {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                name: "Late Job Works",
                res_model: "main.jobwork",
                domain,
                views: [
                    [false, "list"],
                    [false, "form"],
                ]
            })
        }
    }

    async viewReceivedProducts(){
        let domain = [['state', '=', 'verified']]
        if (this.state.period > 0){
            domain.push(['date', '>', this.state.current_date])
        }

        const datas = await this.orm.searchRead("mrp.baazar.product.lines", domain, ['barcode'], [])
        const bcode = [datas.map((record) => record.barcode[0])]

        if (bcode[0].length > 1) {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                name: "Weaved Products Received",
                res_model: "mrp.barcode",
                domain: [['id', 'in', bcode[0]]],
                views: [
                    [false, "list"],
                    [false, "form"],
                ]
            })
        }
    }

    async viewWeavingExpense(){
        let domain = [['state', '=', 'posted'], ['bazaar_id', '!=', false]]
        if (this.state.period > 0){
            domain.push(['date', '>', this.state.current_date])
        }
        const data = await this.orm.searchCount("account.move", domain)

        if (data > 0) {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                name: "Weaving Vendor Bills",
                res_model: "account.move",
                domain,
                views: [
                    [false, "list"],
                    [false, "form"],
                ]
            })
        }
    }
}

OwlWeavingDashboard.template = 'owl.OwlWeavingDashboard'
OwlWeavingDashboard.components = { KpiCard, ChartRenderer }

registry.category('actions').add("owl.weaving_dashboard", OwlWeavingDashboard)
