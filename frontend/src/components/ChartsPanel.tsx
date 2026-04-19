import {
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { TippingPointState } from '../types'

type Props = {
  series: Array<Record<string, number>>
  tippingPoints: Record<string, TippingPointState>
}

const tippingPointColors: Record<string, string> = {
  trust_collapse: '#2563eb',
  social_contagion: '#059669',
  churn_cascade: '#dc2626',
  extractive_divergence: '#d97706',
}

const tooltipStyle = {
  backgroundColor: 'var(--chart-tooltip-bg)',
  border: '1px solid var(--chart-tooltip-border)',
  borderRadius: '12px',
  color: 'var(--text-main)',
}

// Round tooltip values: 4 decimal places for ratios/probabilities, 1 for large numbers.
const fmtTooltip = (value: number | string) => {
  if (typeof value !== 'number') return value
  if (Math.abs(value) < 10) return value.toFixed(4)
  return value.toLocaleString('en-US', { minimumFractionDigits: 1, maximumFractionDigits: 1 })
}

function renderTippingLines(tippingPoints: Record<string, TippingPointState>) {
  // Labels are intentionally omitted — the TippingPoints panel already explains each trigger.
  // Inline labels cause overlap when multiple tipping points fire close together.
  return Object.entries(tippingPoints)
    .filter(([, point]) => point.triggered && point.step !== null)
    .map(([key, point]) => (
      <ReferenceLine
        key={key}
        x={point.step as number}
        stroke={tippingPointColors[key] ?? '#64748b'}
        strokeDasharray="6 4"
        strokeWidth={2}
        ifOverflow="extendDomain"
      />
    ))
}

export function ChartsPanel({ series, tippingPoints }: Props) {
  return (
    <section className="panel">
      <div className="panel-header">
        <h2>Simulation charts</h2>
        <p>Time series from the DataCollector. Dashed vertical lines mark triggered tipping points.</p>
      </div>
      <div className="chart-grid">
        {/* 1. Trust over time (by user type) */}
        <div className="chart-card">
          <h3>Average trust over time</h3>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={series}>
              <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="3 3" />
              <XAxis dataKey="step" stroke="var(--chart-axis)" tick={{ fill: 'var(--chart-axis)' }} />
              <YAxis domain={[0, 1]} stroke="var(--chart-axis)" tick={{ fill: 'var(--chart-axis)' }} />
              <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: 'var(--text-main)' }} formatter={fmtTooltip} />
              <Legend verticalAlign="bottom" wrapperStyle={{ color: 'var(--text-main)', paddingTop: 8 }} />
              {renderTippingLines(tippingPoints)}
              <Line type="monotone" dataKey="mean_trust" name="Mean trust (active)" stroke="#2563eb" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="mean_trust_all" name="Mean trust (all incl. churned)" stroke="#93c5fd" dot={false} />
              <Line type="monotone" dataKey="avg_trust_skeptic" name="Skeptic" stroke="#f97316" strokeDasharray="5 3" dot={false} />
              <Line type="monotone" dataKey="avg_trust_naive" name="Naive" stroke="#22c55e" strokeDasharray="5 3" dot={false} />
              <Line type="monotone" dataKey="avg_trust_activist" name="Activist" stroke="#ef4444" strokeDasharray="5 3" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* 2. Active users over time */}
        <div className="chart-card">
          <h3>Active users</h3>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={series}>
              <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="3 3" />
              <XAxis dataKey="step" stroke="var(--chart-axis)" tick={{ fill: 'var(--chart-axis)' }} />
              <YAxis stroke="var(--chart-axis)" tick={{ fill: 'var(--chart-axis)' }} />
              <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: 'var(--text-main)' }} formatter={fmtTooltip} />
              <Legend verticalAlign="bottom" wrapperStyle={{ color: 'var(--text-main)', paddingTop: 8 }} />
              {renderTippingLines(tippingPoints)}
              <Line type="monotone" dataKey="active_users" name="Active users" stroke="#0d9488" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* 3. Word-of-mouth (negative + positive) */}
        <div className="chart-card">
          <h3>Word-of-mouth per step</h3>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={series}>
              <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="3 3" />
              <XAxis dataKey="step" stroke="var(--chart-axis)" tick={{ fill: 'var(--chart-axis)' }} />
              <YAxis stroke="var(--chart-axis)" tick={{ fill: 'var(--chart-axis)' }} />
              <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: 'var(--text-main)' }} formatter={fmtTooltip} />
              <Legend verticalAlign="bottom" wrapperStyle={{ color: 'var(--text-main)', paddingTop: 8 }} />
              {renderTippingLines(tippingPoints)}
              <Line type="monotone" dataKey="step_negative_wom_count" name="Negative WOM" stroke="#ef4444" dot={false} />
              <Line type="monotone" dataKey="step_positive_wom_count" name="Positive WOM" stroke="#22c55e" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* 4. Cumulative churn by user type */}
        <div className="chart-card">
          <h3>Cumulative churn by user type</h3>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={series}>
              <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="3 3" />
              <XAxis dataKey="step" stroke="var(--chart-axis)" tick={{ fill: 'var(--chart-axis)' }} />
              <YAxis stroke="var(--chart-axis)" tick={{ fill: 'var(--chart-axis)' }} />
              <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: 'var(--text-main)' }} formatter={fmtTooltip} />
              <Legend verticalAlign="bottom" wrapperStyle={{ color: 'var(--text-main)', paddingTop: 8 }} />
              {renderTippingLines(tippingPoints)}
              <Line type="monotone" dataKey="churn_count_skeptic" name="Skeptic" stroke="#f97316" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="churn_count_naive" name="Naive" stroke="#22c55e" strokeWidth={2} dot={false} />
              <Line type="monotone" dataKey="churn_count_activist" name="Activist" stroke="#ef4444" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* 5. Platform reputation */}
        <div className="chart-card">
          <h3>Platform reputation</h3>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={series}>
              <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="3 3" />
              <XAxis dataKey="step" stroke="var(--chart-axis)" tick={{ fill: 'var(--chart-axis)' }} />
              <YAxis domain={[0, 100]} stroke="var(--chart-axis)" tick={{ fill: 'var(--chart-axis)' }} />
              <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: 'var(--text-main)' }} formatter={fmtTooltip} />
              <Legend verticalAlign="bottom" wrapperStyle={{ color: 'var(--text-main)', paddingTop: 8 }} />
              {renderTippingLines(tippingPoints)}
              <Line type="monotone" dataKey="platform_reputation" name="Reputation (0-100)" stroke="#9333ea" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>

        {/* 6. Per-step economics — revenue breakdown */}
        <div className="chart-card">
          <h3>Platform economics per step</h3>
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={series}>
              <CartesianGrid stroke="var(--chart-grid)" strokeDasharray="3 3" />
              <XAxis dataKey="step" stroke="var(--chart-axis)" tick={{ fill: 'var(--chart-axis)' }} />
              <YAxis stroke="var(--chart-axis)" tick={{ fill: 'var(--chart-axis)' }} />
              <Tooltip contentStyle={tooltipStyle} labelStyle={{ color: 'var(--text-main)' }} formatter={fmtTooltip} />
              <Legend verticalAlign="bottom" wrapperStyle={{ color: 'var(--text-main)', paddingTop: 8 }} />
              {renderTippingLines(tippingPoints)}
              <ReferenceLine y={0} stroke="var(--chart-axis)" strokeDasharray="3 3" />
              <Line type="monotone" dataKey="step_base_revenue" name="Subscription revenue" stroke="#22c55e" dot={false} />
              <Line type="monotone" dataKey="step_dp_revenue" name="DP extraction revenue" stroke="#f59e0b" dot={false} />
              <Line type="monotone" dataKey="step_costs" name="Costs" stroke="#ef4444" dot={false} />
              <Line type="monotone" dataKey="step_profit" name="Profit" stroke="#1e293b" strokeWidth={2} dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  )
}
