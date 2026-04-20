import type { Metrics } from '../types'

type Props = {
  metrics: Metrics
  steps: number
  maxSteps: number
}

const fmtPct = (v: number) => `${(v * 100).toFixed(1)}%`
const fmtScore = (v: number) => v.toFixed(1)
const fmtMoney = (v: number) => v.toLocaleString('en-US', { minimumFractionDigits: 0, maximumFractionDigits: 0 })

export function KpiCards({ metrics, steps, maxSteps }: Props) {
  const items: [string, string][] = [
    ['Step', `${steps} / ${maxSteps}`],
    ['Mean trust (incl. churned)', fmtPct(metrics.mean_trust_all)],
    ['Mean harm', fmtPct(metrics.mean_harm)],
    ['Weekly churn', fmtPct(metrics.churn_rate)],
    ['Cumulative churn', fmtPct(metrics.cumulative_churn)],
    ['Negative WOM', fmtPct(metrics.negative_wom_rate)],
    ['Reputation (0–100)', fmtScore(metrics.platform_reputation)],
    ['Cumulative revenue', fmtMoney(metrics.cumulative_revenue)],
    ['Cumulative Projected Revenue', fmtMoney(metrics.cumulative_projected_revenue ?? 0)],
  ]

  return (
    <section className="kpi-grid">
      {items.map(([label, value]) => (
        <article className="kpi-card" key={label}>
          <span className="kpi-label">{label}</span>
          <strong className="kpi-value">{value}</strong>
        </article>
      ))}
    </section>
  )
}
