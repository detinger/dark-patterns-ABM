# Version Notes

## v1.7.0 — Reputation & economics overhaul

Fixes the cumulative-revenue-by-intensity behavior where Low intensity showed a large loss with no visible gain and Medium (0.40) vs High (0.80) were economically indistinguishable. Root cause: the platform reputation model latched every dark-pattern scenario to the hard floor (2.0) regardless of intensity, collapsing the reputation-gated revenue rate to an identical value. Agent-level dynamics (trust, harm, WOM, churn, the trust/contagion/cascade tipping points) are **unchanged** — only platform reputation and the economics it drives change.

### Reputation dynamics (mean-reverting)
- `_update_reputation` now **mean-reverts toward an intensity-aware health target** instead of an unbounded additive penalty walk: `health = w·mean_trust_all + (1−w)·(1 − mean_neg_wom)`, `target = FLOOR + (CAP−FLOOR)·clamp(health − INTENSITY_DRAG·intensity − CHURN_DRAG·churn)`, `rep += ADJUST_RATE·(target − rep)`.
- New constants: `REPUTATION_HEALTH_TRUST_WEIGHT = 0.7`, `REPUTATION_ADJUST_RATE = 0.06`, `REPUTATION_INTENSITY_DRAG = 0.25`, `REPUTATION_CHURN_DRAG = 0.15`. Removed: `CHURN_REPUTATION_WEIGHT`, `WOM_REPUTATION_WEIGHT`, `POSITIVE_WOM_REPUTATION_WEIGHT`, `REPUTATION_RECOVERY_RATE`.
- Result: reputation now discriminates intensity (control ≈74, low ≈45, medium ≈18, high →floor) and declines **smoothly** instead of via a late cliff. Both 0-100 and 0-1 reputation now share the same `health` blend.

### Counterfactual / opportunity-cost baseline
- The projected no-dark-pattern revenue was frozen at each scenario's own (depressed) initial reputation, making the control out-earn its own baseline → a nonsensical **negative** opportunity cost (−85k). It now projects an idealized clean platform (full retention at `REPUTATION_HEALTHY_REFERENCE = 75`), so opportunity cost is coherent and **monotonic in intensity** (control ≈22k = just attrition, low 62k, medium 230k, high 403k).

### Unified revenue ledgers
- `platform.short_term_revenue` / `long_term_revenue` are now derived from the **same** components as the charted `cumulative_revenue` (single source of truth) instead of a separate ad-hoc formula. `short_term` = gross booked revenue incl. extraction; `long_term` = sustainable base revenue eroded by churn. The **Extractive Divergence** tipping point now actually rises with extraction (previously the extraction term cancelled out, leaving a pure churn×trust quantity).

### Scenario reputation_range wired
- `reputation_range` in `SCENARIOS` was dead config (never reached the model). It is now passed through `run_scenario` and `service.create` into a new `reputation_range` model parameter, so scenarios start at their configured reputation (control 70–80, high 40–60, …).

### Result (N=500, seed 42, 312 steps)
- Cumulative revenue now **monotonic**: control 661k > low 622k > medium 454k > high 280k (was control 724k > low 442k > medium 255k ≈ high 241k).
- Medium-vs-High revenue gap: **38%** (was 5.4%).
- Aggressive dark patterns now show the **short-term-gain / long-term-loss reversal** (net value crosses below control ≈ step 115).

> Note: paper Table I (reputation, revenue, opportunity-cost rows) and the economic figures need re-running via the replication package; agent-side rows (churn, trust, harm, trust/contagion/cascade tipping points) are unaffected.

---

## v1.6.0 — Churn calibration and KPI refinements

Fixes unrealistically high baseline churn for healthy platforms and updates dashboard KPI labels for clarity.

### Churn model calibration
- **Trust-deficit dead zone** (`CHURN_TRUST_DEAD_ZONE = 0.30`) — the logistic churn formula now subtracts a dead zone from the trust deficit before applying the trust weight. Users with trust above ~0.70 experience zero trust-driven churn pressure. Only when trust drops meaningfully does the deficit start driving exits.
- **Intercept lowered** (`THETA0`: -7.00 → -8.00) — reduces the baseline churn probability for all users, so healthy platforms maintain a near-steady active user base.
- **Trust weight raised** (`THETA_TRUST`: 2.80 → 3.50) — compensates for the dead zone so that low-trust users (from dark-pattern exposure) still churn at a meaningful rate.

### Result
- Healthy platform (intensity=0): **6.6% cumulative churn** over 312 steps (was 26.2%)
- Dark-pattern platform (intensity=0.40): **53.2% cumulative churn** (strong contrast preserved)

### Frontend
- **Mean trust KPI** renamed to **Mean trust (incl. churned)** and now shows `mean_trust_all` (all users including churned) instead of active-only trust.
- **Projected revenue KPI** renamed to **Cumulative Projected Revenue** and now shows `cumulative_projected_revenue` instead of `long_term_revenue`.
- `cumulative_projected_revenue` added to TypeScript `Metrics` interface.

---

## v1.5.0 — Trust rebound fix and frontend UX redesign

Fixes a survivorship-driven trust rebound where active user trust recovered to near-baseline levels despite ongoing dark-pattern exposure, and redesigns the frontend control panel for clarity.

### Trust recovery fixes
- **Harm-adjusted recovery ceiling** — trust can no longer recover to full baseline. Recovery caps at `baseline × (1 − harm)`, so accumulated harm permanently depresses the ceiling.
- **Intensity-dampened recovery** — both customer support and natural trust recovery are multiplied by `(1 − dark_pattern_intensity)`. At 0.40 intensity, recovery runs at 60% effectiveness.
- **Positive WOM harm gate** — only users with zero harm and zero cumulative exposure can spread positive WOM. Previously, harmed survivors could spread positive sentiment while simultaneously generating negative WOM.
- **Positive WOM capped at recovery ceiling** — positive WOM boosts are capped at the harm-adjusted ceiling, not the original baseline.

### Config tuning
- `POSITIVE_WOM_TRUST_BOOST` reduced from 0.30 to 0.10 (per-message boost: +0.018 vs +0.054).
- `POSITIVE_WOM_BASE_RATE` reduced from 0.20 to 0.10.

### Backend
- `dark_pattern_intensity` now stored as a model attribute (was only passed through to DarkPattern objects).

### Frontend UX redesign
- **Form mode state machine** — three modes: `create-fresh` (editable defaults when no sim loaded), `viewing` (disabled form showing loaded sim's params), `create-editing` (editable form for creating a new sim).
- **Form syncs from backend** — loading a simulation populates all form fields with that simulation's actual parameters.
- **Auto-zero intensity** — unchecking all dark pattern checkboxes automatically zeros the intensity slider and disables it until at least one pattern is re-enabled.
- **Clear UX separation** — simulation run controls (step, run, reset, live, export) are visually separated from the creation form. The form is grayed out when viewing, with a "New simulation" button to enter editing mode.

---

## v1.4.0 — Realistic WOM spread and trust dynamics

WOM spread and trust decline are now gradual and realistic instead of explosive. At medium intensity, trust erodes over months rather than collapsing in the first few weeks.

### WOM mechanics
- **Cooldown threshold** — users must accumulate harm ≥ 0.08 before spreading any negative WOM. No more day-one complaints.
- **Gradual ramp-up** — once past cooldown, WOM probability scales with accumulated harm (0→100% over harm range 0.08–0.33).
- **Global damping factor** (0.35) — all per-neighbor spread probabilities reduced to prevent cascade.
- **Per-step neighbor limit** (max 3) — models realistic social interaction limits.
- **Activist personality ranges narrowed** — social_activity (0.70–0.95 → 0.45–0.70), complaint_propensity (0.60–0.85 → 0.40–0.60).

### Receiver skepticism
- **Diminishing returns** — repeated WOM messages in the same step have decreasing impact (1st: 100%, 2nd: 67%, 3rd: 50%).
- **Trust shield** — high-trust users discount WOM more (trust=0.9 → only 46% impact, trust=0.1 → 94% impact).

### Trust recovery
- **Partial recovery during exposure** — customer support now provides proportional recovery even when exposed (light exposure: 67% recovery, heavy: 0%).
- **Natural trust recovery** — small passive drift toward trust baseline each step (0.004 × gap).
- **BETA_SUPPORT_RECOVERY** tuned to 0.14 (was 0.10).

### Simulation defaults
- **Default max steps** increased from 104 to 312 (6 years at 1 step/week) to accommodate slower dynamics.
- **Reputation floor** lowered from 5.0 to 2.0.

### Result at medium intensity (500 users, intensity=0.50)
- Steps 1–15: zero WOM, trust stable at 0.73
- Step 30: trust 0.66, WOM building (145/step)
- Step 50: trust 0.50, 35 churned
- Step 104: trust 0.40, 178/500 churned (35.6%)

---

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
