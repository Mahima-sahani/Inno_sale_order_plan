/** @odoo-module */

import { registry } from "@web/core/registry"
import { loadJS } from "@web/core/assets"
const { Component, onWillStart, useRef, onMounted, useEffect, onWillUnmount } = owl
import { useService } from "@web/core/utils/hooks"

export class ChartRenderer extends Component {
    setup(){
        this.chartRef = useRef("chart")
        this.actionService = useService("action")

        onWillStart(async ()=>{
            await loadJS("https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.0/chart.umd.min.js")
        })

        useEffect(()=>{
            this.renderChart()
        }, ()=>[this.props.config])

        onMounted(()=>this.renderChart())

        onWillUnmount(()=>{
            if (this.chart) {
                this.chart.destroy()
            }
        })
    }

    renderChart(){
        const old_chartJs = document.querySelector('script[src="web/static/lib/Chart/Chart.js"]')

        if (old_chartJs) {
            return
        }

        if (this.chart) {
            this.chart.destroy()
        }
        this.chart = new Chart(this.chartRef.el,
        {
          type: this.props.type,
          data: this.props.config.data,
          options: {
            onClick: (e)=> {
                const active = e.chart.getActiveElements()
                if (active.length > 0) {
                    let label = e.chart.data.labels[active[0].index]
                    let dataset = e.chart.data.datasets[active[0].datasetIndex].label

                    let { field_check, model, domain, label_id, check_label } = this.props.config

                    let new_domain = domain ? domain : []

                    if (label_id) {
                        label = parseInt(label.split(': ')[1])
                    }

                    if (field_check) {
                        if (field_check.includes('issue_date')) {

                            const timeStamp = Date.parse(label)
                            const selectedMonth = moment(timeStamp)
                            const monthStart = selectedMonth.format('DD/MM/YYYY')
                            const monthEnd = selectedMonth.endOf('month').format('DD/MM/YYYY')
                            new_domain.push(['issue_date', '>=', monthStart], ['issue_date', '<=', monthEnd])
                        }
                        else {
                            new_domain.push([field_check, '=', label])
                        }
                    }

                    if (check_label) {
                        if (dataset == undefined) {
                            new_domain.push(['division_id', '=', false])
                        }
                        else {
                            new_domain.push(['division_id.name', '=', dataset])
                        }
                    }

                    if (dataset == 'On Time') {
                        new_domain.push(['remaining_days', '>=', 0])
                    }

                    if (dataset == 'Late') {
                        new_domain.push(['remaining_days', '<', 0])
                    }


                    if (model) {
                        this.actionService.doAction({
                        type: "ir.actions.act_window",
                        name: this.props.title,
                        res_model: model,
                        domain: new_domain,
                        views: [
                            [false, "list"],
                            [false, "form"],
                        ]
                    })
                    }
                }
            },
            responsive: true,
            plugins: {
              legend: {
                position: 'bottom',
              },
              title: {
                display: true,
                text: this.props.title,
                position: 'bottom',
              }
            }
          },
        }
      );
    }
}

ChartRenderer.template = "owl.ChartRenderer"