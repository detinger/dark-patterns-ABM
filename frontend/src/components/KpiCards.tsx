import type { Metrics } from '../types'

type Props = {
  metrics: Metrics
  steps: number
  maxSteps: number
}

// Ratios and probabilities: 3 decimal places.
const fmt3 = (v: number) => v.toFixed(3)
// Larger counts / currency: 1 decimal place with thousands separator.
const fmtBig = (v: number) => v.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 })

export function KpiCards({ metrics, steps, maxSteps }: Props) {
  const items: [string, string][] = [
    ['Step', `${steps} / ${maxSteps}`],
    ['Mean trust', fmt3(metrics.mean_trust)],
    ['Mean harm', fmt3(metrics.mean_harm)],
    ['Weekly churn', fmt3(metrics.churn_rate)],
    ['Cumulative churn', fmt3(metrics.cumulative_churn)],
    ['Negative WOM', fmt3(metrics.negative_wom_rate)],
    // platform_reputation is the persistent 0-100 score (same scale as the chart)
    ['Reputation (0–100)', fmt3(metrics.platform_reputation)],
    // short_term_revenue accumulates across all steps (gross cumulative revenue)
    ['Cumulative revenue', fmtBig(metrics.cumulative_revenue)],
    // long_term_revenue discounts gross by cumulative churn × mean trust
    ['Projected revenue', fmtBig(metrics.long_term_revenue ?? 0)],
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
