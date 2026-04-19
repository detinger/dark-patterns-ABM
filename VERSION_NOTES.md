# Version Notes

## v1.3.0 — Reputation-discounted revenue and economics visualization

Platform economics now respond realistically to reputation collapse, and the dashboard shows three economics charts telling the full story of dark-pattern consequences.

### Simulation mechanics
- **Reputation-discounted revenue** — revenue per user scales with platform reputation via `(reputation / 100) ^ 0.5`. A platform at reputation 6/100 earns only 25% of its full-reputation rate. Applied to both subscription revenue and dark-pattern extraction revenue.
- **Opportunity cost tracking** — model tracks projected revenue (all users retained, full initial reputation) vs actual revenue. The gap is the cumulative cost of dark patterns.

### Frontend
- **Per-step economics chart** — shows step revenue, costs, and profit. Revenue visibly declines as users churn and reputation drops. Profit can go negative.
- **Cumulative economics chart** — cumulative revenue, costs, and net value. Starts from INITIAL_CUMULATIVE_REVENUE (10,000).
- **Cost of dark patterns chart** — projected revenue (no DP) vs actual revenue vs opportunity cost. The growing gap directly measures the price of dark patterns.

---

## v1.2.0 — Realism mechanics and frontend polish

Ported and expanded simulation mechanics from the standalone DarkPatternsABM research project.

### Simulation mechanics
- **Beta trait sampling** — agent traits drawn from Beta(5,5) distributions instead of uniform, producing bell-shaped variation
- **Exposure buildup ramp** — first 3 encounters with a pattern deliver 20%→67%→100% harm
- **Harm saturation** — harm grows logistically, saturating at 1.0 (models desensitisation)
- **Harm-dampened recovery** — customer support effectiveness decays as cumulative harm grows
- **Natural attrition** — 0.01% background churn per agent per step
- **Trust resilience** — naive users dampen 30–50% of trust loss (rationalise bad UX)
- **Hidden extraction revenue** — undetected dark-pattern exposures earn 1.5× normal revenue
- **Reputation floor** — platform reputation cannot drop below 5/100
- **Initial platform revenue** — simulations start with 10,000 cumulative revenue (existing traction)

### Calibration
- **Churn intercept** recalibrated (θ₀: -5.50 → -7.00) for ~70% cumulative churn at intensity 0.4 over 2 years instead of 92%
- **Trust loss cap** reduced (0.05 → 0.035 per step) for slower trust erosion
- **WOM formula** reweighted: harm-gated (requires harm > 0), increased harm/trust weight, reduced trait weight

### Frontend
- Fixed churn-by-type chart (was empty due to mismatched dataKeys)
- Fixed trust-per-type lines (same dataKey mismatch)
- Tooltips now show percentages for trust/churn, integers for counts, formatted currency for economics
- KPI cards show human-readable percentages
- Economics chart split into subscription revenue + DP extraction revenue
- Legend moved below charts (was overlapping tipping-point lines)
- Tipping-point inline labels removed (redundant with panel)
- Revenue KPIs renamed for clarity (Cumulative revenue, Projected revenue)
- Reputation KPI now uses 0–100 scale matching the chart

### Scenarios
- `social_influence_strength` and `retention_bonus` now forwarded from scenario presets to model

---

## v1.1.0 — Combined research model

Full rewrite of the simulation core, merging the web dashboard with a research-grade agent-based model.

### Model rewrite
- **User types** — 3 heterogeneous types (skeptic 30%, naive 50%, activist 20%) with distinct trait ranges
- **Per-pattern detection** — exposure → detection → harm pipeline with pattern-specific profiles
- **Doc formula coefficients** — explicit α (trust loss), β (recovery), γ (social loss), δ (harm gain)
- **Logistic churn** — θ₀ + θ_trust·(1−T) + θ_harm·H + θ_social·WOM − θ_sc·switching_cost
- **Positive WOM** — satisfied users spread trust-boosting signals
- **Platform economics** — base revenue, churn costs, support costs, WOM damage, short/long-term revenue
- **Platform reputation** — 0–100 score with churn/WOM penalties and recovery
- **Tipping-point detection** — 4 rules with persistence windows

### Backend
- `patterns.py` — DarkPattern dataclass with exposure/detection/harm calculations
- `agents.py` — UserAgent with full pipeline, PlatformAgent with adaptation
- `metrics.py` — 57+ DataCollector reporters (aggregate, per-type, per-pattern, tipping points)
- `analysis.py` — tipping-point detection, summary statistics, scenario/platform comparison
- `run.py` — CLI runner with 6-panel chart output
- `experiments.py` — batch experiment runner with CSV export
- 45+ tests for config, patterns, model, and analysis

### Frontend
- 6-panel chart grid (trust, active users, WOM, churn by type, reputation, economics)
- Scenario support in API and frontend types
- 10 scenario presets (control, low/medium/high intensity, per-pattern, mixed, adaptive, clean competitor)

---

## v1.0.0 — Initial web dashboard

Foundation: Mesa-based ABM with FastAPI backend and React frontend.

### Backend
- Mesa model with basic trust erosion and churn mechanics
- FastAPI endpoints: create, step, reset, get state, timeseries, export CSV, delete
- WebSocket live streaming with configurable interval
- In-memory session management
- Deterministic backward stepping via replay

### Frontend
- React + TypeScript + Vite dashboard
- Simulation creation form with parameter sliders
- KPI cards, time-series charts (Recharts), network graph (react-force-graph)
- Live run mode with WebSocket/Polling transport toggle and speed slider
- CSV export, session list with load/delete
- Dark mode
- Google Colab notebook for standalone analysis
