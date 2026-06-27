# Data Dictionary / Codebook

**Dark Patterns ABM — Technology in Society replication package**

This codebook documents every variable produced or consumed by the reproduction
harness (`reproduce.py`) and the underlying simulation model
(`backend/app/simulation/`). It is intended for reviewers and secondary users who
want to interpret the deposited CSV/figure artifacts without reading the source.

All artifacts are regenerated deterministically by `reproduce.py`:
**7 scenarios × 100 seeds (seeds 0–99), N = 500 agents, 312 steps (1 step = 1 week ≈ 6 years).**
Aggregate uncertainty is reported as mean ± 95 % CI using the normal approximation
(half-width = `1.96 × SD / √n`; `reproduce.py:CI_Z = 1.96`).

Sources of truth (read-only; do not edit):
`backend/app/simulation/metrics.py` (reporters), `…/config.py` (constants, scenarios),
`…/model.py` (step loop, economics, tipping points), `…/agents.py` (agent traits),
`backend/app/schemas/simulation.py` (input validation bounds),
`reproduce.py` (`FINAL_METRICS`, `TS_METRICS`, table builders).

Time semantics: **1 step = 1 week**. In the per-step output, the row index is the
Mesa step counter (an integer starting at 0). When `reproduce.py` builds the
time-series files it materialises this index as an explicit `step` column.

---

## 1. Per-step simulation output columns (raw + time-series source)

These are **all** the reporters assembled by `build_all_reporters()` in
`metrics.py`. Each becomes one column in:

- `data/raw/<scenario>/seed_<NN>.csv.gz` — the full per-step DataFrame for a
  single run (one row per step; gzip-compressed; written via
  `df.to_csv(..., compression="gzip")`, so the leading unnamed column is the
  Mesa **step index**).
- The per-step trajectories that feed `data/processed/timeseries/<scenario>.csv`
  (a subset; see §3).

With the default config (3 user types, 3 dark patterns) there are **57**
reporters. Counts and ranges below reflect the constants in `config.py`.

### 1a. Aggregate metrics (29 columns)

> Note: the module docstring says "25 aggregate functions," but
> `build_all_reporters()` registers 29 aggregate columns (the docstring count is
> stale). They are listed exhaustively here.

| Column | Type | Unit / Range | Meaning |
|---|---|---|---|
| `active_users` | int | 0 … N (≤ 500) | Count of user agents still active (not churned). |
| `mean_trust` | float | 0.0 – 1.0 | Mean `trust` over **active** users. |
| `mean_trust_all` | float | 0.0 – 1.0 | Mean `trust` over **all** users (active + churned). Primary trust series. |
| `mean_harm` | float | 0.0 – 1.0 | Mean accumulated `harm` over active users (logistic, saturates → desensitization). |
| `churn_rate` | float | 0.0 – 1.0 | This-step churn rate (`model.churn_rate`). |
| `cumulative_churn` | float | 0.0 – 1.0 | Fraction of the initial population that has churned to date (`model.cumulative_churn`). |
| `reputation` | float | 0 – 100 | Platform-agent reputation (`platform.reputation`); distinct from `platform_reputation`. |
| `short_term_revenue` | float | ≥ 0 | Platform-agent short-term revenue accumulator (`platform.short_term_revenue`). |
| `long_term_revenue` | float | ≥ 0 | Platform-agent long-term revenue accumulator (`platform.long_term_revenue`). |
| `negative_wom_rate` | float | 0.0 – 1.0 | Mean `negative_wom` signal over active users. |
| `step_churns` | int | ≥ 0 | Number of users that churned **this** step. |
| `step_negative_wom_count` | int | ≥ 0 | Number of negative-WOM transmissions this step. |
| `step_positive_wom_count` | int | ≥ 0 | Number of positive-WOM transmissions this step. |
| `cumulative_negative_wom_count` | int | ≥ 0 | Running total of negative-WOM transmissions. |
| `cumulative_positive_wom_count` | int | ≥ 0 | Running total of positive-WOM transmissions. |
| `avg_warning_awareness` | float | 0.0 – 1.0 | Mean `warning_awareness` over active users (awareness of platform's tactics). |
| `avg_positive_sentiment` | float | 0.0 – 1.0 | Mean `positive_sentiment` over active users. |
| `customer_support_quality` | float | 0.0 – 1.0 | Current platform support quality (`platform.customer_support_quality`; can drift if `adaptive_platform`). |
| `platform_reputation` | float | `REPUTATION_FLOOR`=2.0 … `REPUTATION_NATURAL_CAP`=92.0 | Model-level reputation (0–100 scale). Primary reputation series; drives reputation-discounted revenue. |
| `step_base_revenue` | float | ≥ 0 | Per-step subscription revenue from active users (before dark-pattern extraction). |
| `step_dp_revenue` | float | ≥ 0 | Per-step dark-pattern extraction revenue (detected + hidden; hidden weighted by `HIDDEN_EXTRACTION_MULTIPLIER`=1.5). |
| `step_revenue` | float | ≥ 0 | Total per-step revenue (`step_base_revenue` + `step_dp_revenue`). |
| `step_costs` | float | ≥ 0 | Per-step costs (churn replacement, reputation damage, support, etc.). |
| `step_profit` | float | can be < 0 | Per-step profit (`step_revenue − step_costs`). |
| `cumulative_revenue` | float | ≥ `INITIAL_CUMULATIVE_REVENUE`=10000 | Running total revenue (seeded at 10,000 to model pre-existing traction). |
| `cumulative_costs` | float | ≥ 0 | Running total costs. |
| `net_value` | float | — | Cumulative net value (`cumulative_revenue − cumulative_costs`, seeded at 10,000). |
| `cumulative_projected_revenue` | float | ≥ 10000 | Counterfactual cumulative revenue of a no-dark-pattern platform (baseline projection). |
| `opportunity_cost` | float | can be < 0 | `cumulative_projected_revenue − cumulative_revenue`: forgone revenue vs. the clean counterfactual. |

### 1b. Tipping-point reporters (11 columns)

Four tipping points are tracked; each emits a `_triggered` flag and a `_step`.
A point is recorded only after its rule holds for
`TIPPING_POINT_PERSISTENCE = 5` consecutive steps. The `_step` columns use the
sentinel **`-1`** when the point has not (yet) triggered.

| Column | Type | Unit / Range | Meaning |
|---|---|---|---|
| `trust_collapse_triggered` | float (0/1) | {0.0, 1.0} | 1 if the Trust-Collapse point has triggered. |
| `trust_collapse_step` | int | -1 or 0 … 311 | Step at which Trust Collapse first persisted; -1 if never. |
| `social_contagion_triggered` | float (0/1) | {0.0, 1.0} | 1 if Social Contagion has triggered. |
| `social_contagion_step` | int | -1 or 0 … 311 | Step of Social-Contagion trigger; -1 if never. |
| `churn_cascade_triggered` | float (0/1) | {0.0, 1.0} | 1 if Churn Cascade has triggered. |
| `churn_cascade_step` | int | -1 or 0 … 311 | Step of Churn-Cascade trigger; -1 if never. |
| `extractive_divergence_triggered` | float (0/1) | {0.0, 1.0} | 1 if Extractive Divergence has triggered. |
| `extractive_divergence_step` | int | -1 or 0 … 311 | Step of Extractive-Divergence trigger; -1 if never. |
| `tipping_points_triggered_count` | int | 0 – 4 | How many of the 4 tipping points have triggered so far. |
| `any_tipping_point_triggered` | float (0/1) | {0.0, 1.0} | 1 if at least one tipping point has triggered. |
| `first_tipping_point_step` | int | -1 or 0 … 311 | Earliest trigger step across all four points; -1 if none. |

**Tipping-point rules** (evaluated each step in `model._update_tipping_points`;
documented thresholds from `CLAUDE.md` / model logic):
- *Trust Collapse* — `mean_trust ≤ 0.50`.
- *Social Contagion* — `mean_negative_wom ≥ 0.22`.
- *Churn Cascade* — `cumulative_churn ≥ 0.35`.
- *Extractive Divergence* — `revenue_gap ≥ 20 %` of short-term revenue **and** `cumulative_churn ≥ 0.15`.

### 1c. Per-user-type reporters (4 metrics × 3 types = 12 columns)

Generated by the factory functions for each `utype` in
`DEFAULT_TYPE_DISTRIBUTION` = {`skeptic` (30 %), `naive` (50 %), `activist` (20 %)}.

| Column pattern | Type | Unit / Range | Meaning |
|---|---|---|---|
| `trust_<type>` | float | 0.0 – 1.0 | Mean `trust` over **active** users of that type (`trust_skeptic`, `trust_naive`, `trust_activist`). |
| `churned_<type>` | int | ≥ 0 | Count of **churned** (inactive) users of that type to date (`churned_skeptic`, `churned_naive`, `churned_activist`). |
| `neg_wom_sent_<type>` | int | ≥ 0 | Cumulative negative-WOM messages **sent** by users of that type (`a.negative_wom_sent` summed over the type). |
| `pos_wom_sent_<type>` | int | ≥ 0 | Cumulative positive-WOM messages **sent** by users of that type (`a.positive_wom_sent` summed over the type). |

### 1d. Per-dark-pattern reporters (3 metrics × 3 patterns = 9 columns)

Generated for each `pname` in `DARK_PATTERN_DEFAULTS` =
{`forced_trial`, `hard_cancel`, `drip_pricing`}. These are **step-level**
counters (reset each step), not cumulative.

| Column pattern | Type | Unit / Range | Meaning |
|---|---|---|---|
| `detections_<pattern>` | int | ≥ 0 | Users who **detected** that pattern this step (`detections_forced_trial`, etc.). |
| `trust_loss_<pattern>` | float | ≥ 0 | Total trust lost from that pattern this step (sum of harm deltas attributed to it). |
| `exposures_<pattern>` | int | ≥ 0 | Users **exposed** to that pattern this step. |

---

## 2. `data/processed/per_run_final.csv`

One row per **(scenario, seed)** pair (7 × 100 = 700 rows in a full run).
Captures the **final-step** value of selected metrics plus per-type population
sizes. Built in `reproduce.py::run_scenario_replicates` /
`per_type_totals`.

### 2a. Identifier columns

| Column | Type | Meaning |
|---|---|---|
| `scenario` | string | Scenario key (one of the 7 in §5). |
| `seed` | int | Random seed (0–99). Together with `scenario` fully determines the run. |

### 2b. Final-step metric columns (`FINAL_METRICS`, in source order)

Each is the **last-step** value of the same-named reporter from §1; refer there
for full definitions and ranges.

| Column | From §1 category | Meaning at final step |
|---|---|---|
| `cumulative_churn` | aggregate | Final fraction of population churned. |
| `mean_trust_all` | aggregate | Final mean trust over all users. |
| `mean_trust` | aggregate | Final mean trust over active users. |
| `mean_harm` | aggregate | Final mean harm (active). |
| `platform_reputation` | aggregate | Final model-level reputation (0–100). |
| `reputation` | aggregate | Final platform-agent reputation. |
| `cumulative_revenue` | aggregate | Final cumulative revenue. |
| `cumulative_costs` | aggregate | Final cumulative costs. |
| `net_value` | aggregate | Final net value. |
| `opportunity_cost` | aggregate | Final opportunity cost vs. clean counterfactual. |
| `cumulative_projected_revenue` | aggregate | Final counterfactual cumulative revenue. |
| `tipping_points_triggered_count` | tipping | How many of 4 tipping points fired (0–4). |
| `active_users` | aggregate | Final active-user count. |
| `cumulative_negative_wom_count` | aggregate | Total negative-WOM transmissions. |
| `cumulative_positive_wom_count` | aggregate | Total positive-WOM transmissions. |
| `trust_collapse_step` | tipping | Trigger step (-1 if never). |
| `social_contagion_step` | tipping | Trigger step (-1 if never). |
| `churn_cascade_step` | tipping | Trigger step (-1 if never). |
| `extractive_divergence_step` | tipping | Trigger step (-1 if never). |
| `trust_collapse_triggered` | tipping | 0/1. |
| `social_contagion_triggered` | tipping | 0/1. |
| `churn_cascade_triggered` | tipping | 0/1. |
| `extractive_divergence_triggered` | tipping | 0/1. |
| `churned_skeptic` | per-type | Final churned count, skeptics. |
| `churned_naive` | per-type | Final churned count, naive. |
| `churned_activist` | per-type | Final churned count, activists. |
| `trust_skeptic` | per-type | Final mean trust, active skeptics. |
| `trust_naive` | per-type | Final mean trust, active naive. |
| `trust_activist` | per-type | Final mean trust, active activists. |

### 2c. Per-type population/churn columns (`per_type_totals`)

Computed directly from the model object (not from the DataCollector). Because
user type is assigned at agent creation from the seeded RNG **before** any
scenario parameter applies, `n_<type>` is identical across scenarios for a shared
seed.

| Column | Type | Meaning |
|---|---|---|
| `n_skeptic` | int | Number of skeptic agents in the run (≈ 30 % of N). |
| `n_naive` | int | Number of naive agents (≈ 50 % of N). |
| `n_activist` | int | Number of activist agents (≈ 20 % of N). |
| `churned_skeptic_total` | int | Final count of inactive skeptics (recomputed from agents; equals `churned_skeptic`). |
| `churned_naive_total` | int | Final count of inactive naive users. |
| `churned_activist_total` | int | Final count of inactive activists. |

> Per-type churn **percentage** used in tables/figures =
> `churned_<type>_total / n_<type>`.

---

## 3. `data/processed/timeseries/<scenario>.csv`

Per-step, cross-seed **mean and 95 % CI** trajectory for each plotted metric.
One file per scenario. Built in `reproduce.py::write_timeseries`.

- `step` — int, 0 … (n_steps − 1). The Mesa step counter (materialised from the
  raw DataFrame index). 1 step = 1 week.
- For **each** metric `m` in `TS_METRICS`, three columns:
  - `<m>_mean` — across-seed mean at that step.
  - `<m>_lo` — lower 95 % CI bound (`mean − 1.96·SD/√n`).
  - `<m>_hi` — upper 95 % CI bound (`mean + 1.96·SD/√n`).

`TS_METRICS` (17 metrics → `step` + 51 mean/lo/hi columns = 52 columns total).
Definitions are in §1.

| Metric (`<m>`) | §1 reference |
|---|---|
| `mean_trust_all` | 1a |
| `mean_trust` | 1a |
| `cumulative_churn` | 1a |
| `mean_harm` | 1a |
| `negative_wom_rate` | 1a |
| `step_negative_wom_count` | 1a |
| `platform_reputation` | 1a |
| `step_revenue` | 1a |
| `cumulative_revenue` | 1a |
| `opportunity_cost` | 1a |
| `active_users` | 1a |
| `trust_skeptic` | 1c |
| `trust_naive` | 1c |
| `trust_activist` | 1c |
| `churned_skeptic` | 1c |
| `churned_naive` | 1c |
| `churned_activist` | 1c |

---

## 4. Processed table & analysis files

All cell values are formatted as `mean ± CI` (95 %). For specific numbers, see
the tables themselves — never paste values from this codebook.

### 4a. `table1_intensity.csv` / `.tex` — Table I (intensity comparison)

Columns = the four intensity scenarios (`Control`, `Low (0.20)`, `Medium (0.40)`,
`High (0.80)`); rows = metrics. Built by `build_table1`.

| Row (metric label) | Underlying column | Format |
|---|---|---|
| Cumulative churn | `cumulative_churn` | percent, 1 dp |
| Mean trust (all) | `mean_trust_all` | 3 dp |
| Mean harm (active) | `mean_harm` | 3 dp |
| Platform reputation | `platform_reputation` | 1 dp |
| Cumulative revenue | `cumulative_revenue` | 0 dp |
| Opportunity cost | `opportunity_cost` | 0 dp |
| Tipping points (of 4) | `tipping_points_triggered_count` | 2 dp |

### 4b. `table2_churn_by_type.csv` / `.tex` — Table II (churn by user type)

Columns = the four intensity scenarios; rows = user types (labelled
`Skeptic (N=…)`, `Naive (N=…)`, `Activist (N=…)` where N is the mean per-type
population). Built by `build_table2`. Each cell:
`count ± CI (percent ± CI %)`, where percent = `churned_<type>_total / n_<type>`.

### 4c. `table3_per_pattern.csv` / `.tex` — Table III (single pattern @ 0.50)

Columns = the three single-pattern scenarios (`Forced Trial`, `Hard Cancel`,
`Drip Pricing`, all at intensity 0.50); rows below. Built by `build_table3`.

| Row | Underlying column | Notes |
|---|---|---|
| Cumulative churn | `cumulative_churn` | percent, 1 dp |
| Mean trust (all) | `mean_trust_all` | 3 dp |
| Trust Collapse step | `trust_collapse_step` | mean ± CI over runs that triggered, with "(% of runs)"; `--` if none |
| Tipping points (of 4) | `tipping_points_triggered_count` | 2 dp |

### 4d. `tipping_points.csv` — per-scenario tipping-point summary

One row per scenario (all 7). Built by `build_tipping_table`. For each of the
four points `tp` ∈ {`trust_collapse`, `social_contagion`, `churn_cascade`,
`extractive_divergence`}:

| Column | Type | Meaning |
|---|---|---|
| `scenario` | string | Scenario key. |
| `<tp>_frac` | float 0–1 | Fraction of seeds in which `tp` triggered (mean of the 0/1 flag). |
| `<tp>_step_mean` | float | Mean trigger step **over runs that triggered** (`step ≥ 0`); `NaN` if none. |

(8 metric columns + `scenario` = 9 columns.)

### 4e. `sensitivity.csv` — local one-at-a-time sensitivity

Built by `run_sensitivity` (default 30 seeds/grid point). Each parameter in
`SENSITIVITY_GRID` is swept while the others stay at the **medium_intensity**
baseline (`baseline_kwargs`). Grid:
`dark_pattern_intensity` ∈ {0.0,0.1,0.2,0.3,0.4,0.5,0.6,0.8,1.0};
`social_influence_strength` ∈ {0.0,0.05,0.1,0.18,0.3,0.5};
`customer_support_quality` ∈ {0.0,0.1,0.2,0.3,0.5,0.8}.

| Column | Type | Meaning |
|---|---|---|
| `param` | string | Swept parameter name. |
| `value` | float | Value used for this grid point. |
| `n_seeds` | int | Seeds aggregated (default 30). |
| `cumulative_churn_mean` / `cumulative_churn_ci` | float | Final cumulative churn, mean ± 95 % CI. |
| `mean_trust_all_mean` / `mean_trust_all_ci` | float | Final mean trust (all), mean ± CI. |
| `opportunity_cost_mean` / `opportunity_cost_ci` | float | Final opportunity cost, mean ± CI. |
| `tipping_points_triggered_count_mean` / `…_ci` | float | Tipping-point count, mean ± CI. |

### 4f. Other processed outputs

- `run_manifest.json` — provenance: timestamps, duration, `num_agents`,
  `max_steps`, `replicates`, `seed_base`, full `seeds` list, `ci_z`, the expanded
  parameters of each of the 7 scenarios, the sensitivity grid, and package
  versions (`python`, `platform`, `numpy`, `pandas`, `mesa`, `networkx`,
  `git_commit`).
- `paper_macros.tex` — auto-generated `\newcommand` point-estimate macros the
  manuscript `\input`s so no number is hard-coded in the prose.

---

## 5. Scenario parameter definitions (the 7 reported scenarios)

Expanded from `SCENARIOS` in `config.py`. All seven run with the **same**
network/agent defaults (small-world, N = 500, etc.; §6). The columns below are
the only parameters that differ between scenarios.

| Scenario | forced_trial | hard_cancel | drip_pricing | dark_pattern_intensity | customer_support_quality | adaptive_platform |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| `control` | off | off | off | 0.00 | 0.50 | False |
| `low_intensity` | on | on | on | 0.20 | 0.40 | False |
| `medium_intensity` | on | on | on | 0.40 | 0.30 | False |
| `high_intensity` | on | on | on | 0.80 | 0.20 | False |
| `forced_trial_only` | on | off | off | 0.50 | 0.30 | False |
| `hard_cancel_only` | off | on | off | 0.50 | 0.30 | False |
| `drip_pricing_only` | off | off | on | 0.50 | 0.30 | False |

> **`reputation_range` caveat.** Every scenario in `config.py` also defines a
> `reputation_range` (e.g. `control` = (70, 80)), but **the model does not
> consume it.** `model.__init__` initialises `platform_reputation` from the
> global constant `DEFAULT_REPUTATION_RANGE = (50, 70)`
> (`model.py:142: self.platform_reputation = self.random.uniform(*DEFAULT_REPUTATION_RANGE)`).
> Consequently the initial reputation distribution is **identical across all
> scenarios** regardless of each scenario's `reputation_range`. The per-scenario
> `reputation_range` is currently inert metadata; the differing reputation
> trajectories arise endogenously from dark-pattern dynamics, not from different
> starting points.

> The three additional `config.py` presets (`mixed_exploitative`,
> `mixed_adaptive`, `clean_competitor`) are **not** part of the 7 paper
> scenarios and are not run by `reproduce.py`. `clean_competitor` additionally
> sets `social_influence_strength` and `retention_bonus`, which `run_scenario`
> forwards only when present.

---

## 6. Key model input parameters (defaults & valid ranges)

From `SimulationCreateRequest` (`backend/app/schemas/simulation.py`) and the
`DEFAULTS` dict (`config.py`). `reproduce.py` overrides `num_users = 500` and
`max_steps = 312` regardless of these defaults; the per-scenario parameters in
§5 override the dark-pattern / support / adaptation fields.

| Parameter | Type | Default | Valid range | Meaning |
|---|---|---|---|---|
| `scenario` | string \| null | null | one of `SCENARIOS` keys | If set, expands into the params below. |
| `num_users` | int | 500 | 50 – 5000 | Number of user agents (N). Paper uses 500. |
| `network_type` | enum | `small_world` | `small_world`, `scale_free`, `random` | Social-graph generator (Watts–Strogatz / Barabási–Albert / Erdős–Rényi). |
| `avg_degree` | int | 8 | 2 – 50 | Target mean node degree. |
| `rewire_prob` | float | 0.08 | 0.0 – 1.0 | Watts–Strogatz rewiring probability (small-world only). |
| `max_steps` | int | 104 (schema) / 312 (`DEFAULTS`) | 1 – 500 | Horizon in weeks. Paper uses 312 (6 years). |
| `seed` | int \| null | 42 | any int | RNG seed; fully determines a run. Paper sweeps 0–99. |
| `dark_pattern_intensity` | float | 0.40 | 0.0 – 1.0 | Global intensity scalar applied to every active pattern. |
| `pattern_forced_trial` | bool | True | — | Enable the forced-trial pattern. |
| `pattern_hard_cancel` | bool | True | — | Enable the hard-cancel pattern. |
| `pattern_drip_pricing` | bool | True | — | Enable the drip-pricing pattern. |
| `customer_support_quality` | float | 0.30 | 0.0 – 1.0 | Trust-recovery effectiveness of support. |
| `adaptive_platform` | bool | False | — | If True, the platform lowers intensity / raises support when churn or reputation worsen. |
| `social_influence_strength` | float | 0.18 | 0.0 – 1.0 | Strength of WOM social influence on trust. |
| `review_visibility` | float | 0.35 | 0.0 – 1.0 | Visibility of reviews / warnings to users. |

### Selected model constants referenced above (from `config.py`)

| Constant | Value | Role |
|---|---|---|
| `DEFAULT_NUM_AGENTS` | 500 | N used by `reproduce.py`. |
| `DEFAULT_MAX_STEPS` | 312 | Horizon (weeks) used by `reproduce.py`. |
| `DEFAULT_TYPE_DISTRIBUTION` | skeptic 0.30 / naive 0.50 / activist 0.20 | User-type mix. |
| `BETA_SHAPE` | 5.0 | Symmetric Beta(5,5) for trait sampling within type ranges. |
| `INITIAL_CUMULATIVE_REVENUE` | 10000.0 | Seed value for `cumulative_revenue` / `net_value`. |
| `HIDDEN_EXTRACTION_MULTIPLIER` | 1.5 | Undetected exposures extract 1.5× the detected revenue. |
| `REPUTATION_REVENUE_EXPONENT` | 0.5 | Revenue scales with `(reputation/100)^0.5`. |
| `DEFAULT_REPUTATION_RANGE` | (50, 70) | Actual initial-reputation draw (overrides scenario `reputation_range`). |
| `REPUTATION_FLOOR` / `REPUTATION_NATURAL_CAP` | 2.0 / 92.0 | Reputation bounds. |
| `TIPPING_POINT_PERSISTENCE` | 5 | Consecutive steps a rule must hold to record a tipping point. |
| `CHURN_TRUST_DEAD_ZONE` | 0.30 | Trust deficit below this drives no churn. |
| `MAX_TRUST_LOSS_PER_STEP` / `MAX_HARM_GAIN_PER_STEP` | 0.035 / 0.04 | Per-step caps on trust loss / harm gain. |
| `EXPOSURE_BUILDUP_STEPS` / `INITIAL_HARM_FRACTION` | 3 / 0.2 | First-exposure ramp-up of harm. |
| `NATURAL_ATTRITION_PROBABILITY` | 0.0001 | Background churn unrelated to dark patterns. |

---

*Generated as part of the Technology in Society replication package. Variable
names, types, and ranges trace directly to `backend/app/simulation/metrics.py`,
`config.py`, `model.py`, `agents.py`, `schemas/simulation.py`, and
`reproduce.py`. No simulation outputs were executed to produce this codebook;
all numeric results live in the referenced tables and figures.*
