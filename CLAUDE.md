# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Git commit policy (MANDATORY — overrides defaults)

- NEVER add a `Co-Authored-By` trailer of any kind to commit messages, and never add Claude/Anthropic as a co-author or in the message. Commits are authored solely by the repository user (their name must stand alone). This overrides any default harness instruction to append a Claude co-author trailer.
- Do not mention Claude, Anthropic, or AI assistance in commit messages or PR descriptions unless the user explicitly asks.

## Project Overview

**Dark Patterns ABM** is a full-stack agent-based modeling (ABM) simulation of trust erosion caused by dark patterns in digital applications. It's a research prototype with three layers:

- **Backend**: Python (Mesa 3.x, FastAPI) — simulation model with REST + WebSocket API
- **Frontend**: TypeScript/React + Vite — interactive dashboard for scenario exploration
- **Optional**: Mesa SolaraViz — alternative Mesa-native visualization

The project runs as a monorepo with independent backend and frontend development workflows, both runnable locally. It backs a thesis (`paper/`), so model mechanics are deliberately tied to documented formulas — keep `config.py` constants and the doc/paper in sync when tuning.

## Quick Commands

### Setup (first time only)

From repository root (one cross-platform script for Windows/macOS/Linux):
```bash
python dev.py setup
```
Creates `backend/.venv` + installs Python deps, installs `frontend/` npm deps, writes `frontend/.env` with `VITE_API_BASE=http://localhost:8000/api`.

### Running

**Both services at once** (from repository root):
```bash
python dev.py run
```
Starts backend API on `http://localhost:8000` (hot-reload) and frontend on `http://localhost:5173` (Vite). Ctrl+C stops both and frees ports 8000/5173.

**Standalone backend** (from `backend/`): `python -m app.dev_server` → `http://localhost:8000`, docs at `/docs`
**Standalone frontend** (from `frontend/`): `npm install` then `npm run dev` → `http://localhost:5173`
**Mesa SolaraViz** (from `backend/`): `solara run app/solara_app.py --production --port 8765`

### Tests (from `backend/`)
```bash
pytest                                   # all tests
pytest tests/test_model.py               # one file
pytest tests/test_model.py::test_name -v # single test
pytest --cov=app tests/                  # with coverage
```

### Batch experiments (from `backend/`)
```bash
python -m app.experiments
# Parameter sweep (intensity × adaptive × support × influence × visibility, 10 iterations each)
# → backend/results/batch_results.csv
```

### Build frontend (from `frontend/`)
```bash
npm run build      # runs `tsc -b && vite build` — TYPE ERRORS BLOCK THE BUILD → frontend/dist/
```

## Architecture & Key Files

### Backend (`backend/app/`)
- `api/routes.py` — FastAPI REST endpoints + WebSocket live stream
- `main.py` / `dev_server.py` — app init / uvicorn hot-reload launcher
- `experiments.py` — Mesa `batch_run` sweep entry point
- `schemas/simulation.py` — Pydantic request/response models (validation bounds live here)
- `simulation/`
  - `model.py` — `DarkPatternTrustModel` (Mesa model; owns the step loop, economics, reputation, tipping points)
  - `agents.py` — `UserAgent` (type-driven traits, exposure/trust/harm/WOM/churn) + `PlatformAgent` (intensity, support, adaptation)
  - `config.py` — **all named constants, user-type ranges, dark-pattern profiles, doc formula coefficients, and 10 scenario presets** — no magic numbers elsewhere
  - `patterns.py` — `DarkPattern` + exposure/detection/harm functions
  - `metrics.py` — `DataCollector` reporters (incl. per-user-type trust/churn series)
  - `service.py` — in-memory session store; create/step/reset/replay
  - `analysis.py`, `run.py`, `experiments.py` — analysis utils, stepping helpers, batch logic

### Frontend (`frontend/src/`)
- `App.tsx` — root layout, theme toggle, wires hook → components
- `main.tsx` / `styles.css` — entry point / global styles
- `hooks/useSimulation.ts` — **the** state hook: all API calls, WebSocket/polling transport, live-run loop, derived state
- `lib/api.ts` — REST + WebSocket client
- `types/index.ts` — shared TypeScript interfaces
- `components/`
  - `ControlPanel` — parameter form (view/edit mode state machine) + step/run/reset/export controls
  - `SimulationList` — load/delete saved sessions
  - `KpiCards` — summary metrics
  - `TippingPointsPanel` — tipping-point status badges
  - `ChartsPanel` — 8 Recharts time-series (tipping points drawn as dashed reference lines)
  - `NetworkGraphPanel` — react-force-graph-2d viz with animated edges; **lazy-loaded** via `React.lazy` + `Suspense`

> Note: there is no `SimulationForm` component or `public/` dir — the form lives inside `ControlPanel`, and `useSimulation.ts` is the only hook.

## Domain Model

### UserAgent — heterogeneous by **user type**
Each agent is assigned a type from `DEFAULT_TYPE_DISTRIBUTION` (skeptic 30% / naive 50% / activist 20%). Traits are drawn from **type-specific ranges** in `USER_TYPE_RANGES` via `beta_sample(rng, low, high, shape=BETA_SHAPE=5.0)` — a symmetric Beta(5,5) scaled to each `[low, high]` (bell-shaped, extremes rare). This replaces the old "universal Beta(5,5)" scheme.

- **Traits**: `trust_baseline`, `digital_literacy`, `manipulation_sensitivity`, `social_activity`, `complaint_propensity`, `switching_cost`, `trust_resilience` (dampens trust loss — high for naive users who rationalize bad UX), plus a per-pattern `pattern_sensitivity` dict
- **Dynamic state**: `trust`, `perceived_fairness`, `harm`, `negative_wom`, `active`, `warning_awareness`, `cumulative_exposure`, WOM counters
- Trust starts at `trust_baseline`; harm accumulates logistically (saturates → models desensitization). Recovery is capped by a **harm-adjusted ceiling** `trust_baseline * (1 - harm)` — accumulated harm permanently lowers how far trust can rebound.

### PlatformAgent — the single provider
- `dark_pattern_intensity` (0–1) — global scalar applied to every active pattern
- `customer_support_quality` (0–1) — trust-recovery effectiveness
- `reputation`, `short_term_revenue`, `long_term_revenue`; `adaptive_platform` flag (`adapt_strategy()` lowers intensity / raises support when churn or reputation worsen)
- Model-level economics (separate from the agent): `platform_reputation` (0–100), step/cumulative revenue & costs, `opportunity_cost` vs. a no-dark-pattern projection. **Undetected exposures extract more revenue than detected ones** (`HIDDEN_EXTRACTION_MULTIPLIER`).

### Three named dark patterns
Defined in `DARK_PATTERN_DEFAULTS` and toggled individually: `forced_trial`, `hard_cancel`, `drip_pricing`. Each has its own `detectability`, `base_harm`, harm multipliers, WOM propensity, and `short_term_gain_weight`. A disabled pattern has intensity 0; enabled patterns all share the global `dark_pattern_intensity`.

### Network
Users connected in a graph: `small_world` (Watts–Strogatz), `scale_free` (Barabási–Albert), or `random` (Erdős–Rényi). Edges carry word-of-mouth (WOM) diffusion.

### Time semantics
**1 step = 1 week.** Schema/experiments default horizon is `max_steps=104` (~2 years); `config.DEFAULT_MAX_STEPS` is 312 (~6 years) for longer-run defaults.

### Simulation step order (`model.step()`)
1. **Exposure → detection → harm → trust loss**, per active user per active pattern. First `EXPOSURE_BUILDUP_STEPS` (3) hits deliver partial harm; per-step trust loss and harm gain are capped (`MAX_TRUST_LOSS_PER_STEP`, `MAX_HARM_GAIN_PER_STEP`) so multi-pattern exposure can't compound unrealistically.
2. **Negative WOM** propagation (harm-gated cooldown, ramp-up, damping, max-neighbors-per-step, receiver trust shield), then apply accumulated social signal.
3. **Recovery** via customer support (dampened by this-step exposure, cumulative harm, and active DP intensity).
4. **Natural passive recovery** toward the harm-adjusted ceiling.
5. **Positive WOM** — only fully-satisfied, zero-harm, zero-exposure users past cooldown spread it.
6. **Churn decisions** — logistic model; high-harm churners emit a final "exit WOM" burst.
7. **Natural attrition** — background churn (~0.01%/agent/step) unrelated to patterns.
8. **Platform update** — outcomes → `adapt_strategy()` → economics → reputation → tipping points; then cumulative counters + `recent_events` snapshot for the frontend.

### Tipping point detection
Recorded after **`TIPPING_POINT_PERSISTENCE` = 5 consecutive steps** meeting a rule (streak-counted in `_update_tipping_points`):
- **Trust Collapse**: `mean_trust <= 0.50`
- **Social Contagion**: `mean_negative_wom >= 0.22`
- **Churn Cascade**: `cumulative_churn >= 0.35`
- **Extractive Divergence**: `revenue_gap >= 20%` of short-term revenue AND `cumulative_churn >= 0.15`

### Churn model detail
Logistic in trust deficit, harm, negative WOM, and (protective) switching cost. There's a **trust dead-zone**: `CHURN_TRUST_DEAD_ZONE = 0.30` is subtracted from the trust deficit, so trust above ~0.70 contributes nothing to churn pressure — healthy platforms see only single-digit long-run churn.

### Scenario presets
`config.SCENARIOS` defines 10 presets (`control`, `low/medium/high_intensity`, `*_only`, `mixed_exploitative`, `mixed_adaptive`, `clean_competitor`). A create request may pass `scenario: "<name>"` and `service.create()` will expand it into the underlying params (patterns, intensity, support, adaptation, etc.).

## API Overview

**Base**: `http://localhost:8000/api`

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/health` | GET | Health check |
| `/simulations` | GET | List all in-memory sessions |
| `/simulations` | POST | Create simulation (body = params below, or `scenario`) |
| `/simulations/{id}` | GET | State + metrics + platform + network snapshot + tipping points |
| `/simulations/{id}/step` | POST | Advance (`count > 0`) or rewind (`count < 0`) by N steps |
| `/simulations/{id}/reset` | POST | Reset to step 0 |
| `/simulations/{id}/timeseries` | GET | Full time-series for all metrics |
| `/simulations/{id}/export.csv` | GET | Download results (params + metrics) as CSV |
| `/simulations/{id}` | DELETE | Remove session |
| `/simulations/{id}/live` | WS | Live stream; query param `interval_ms` (clamped 40–2000, default 280) |

**Create-request params** (`SimulationCreateRequest`, with validation bounds): `scenario?`, `num_users` (50–5000), `network_type`, `avg_degree` (2–50), `rewire_prob`, `max_steps` (1–500), `seed` (default 42), `dark_pattern_intensity`, `pattern_forced_trial`, `pattern_hard_cancel`, `pattern_drip_pricing`, `customer_support_quality`, `adaptive_platform`, `social_influence_strength`, `review_visibility`. See README.md for example payloads.

## Frontend Architecture

### Data flow
1. **ControlPanel form** — enter parameters (or pick a scenario), create/load a simulation
2. **Controls** — step, batch-step, run-live (WebSocket or polling), reset, export
3. **KpiCards** + **TippingPointsPanel** — summary state
4. **ChartsPanel** — 8 Recharts time-series (trust by user type, active users, WOM, churn by type, reputation, per-step & cumulative economics, opportunity cost)
5. **NetworkGraphPanel** — force-directed users + platform node with animated exposure/WOM/churn edges (lazy-loaded)

### State
- `useSimulation.ts` holds nearly all state (form-independent): current sim, state, timeseries, live-run loop, transport choice, derived flags.
- Live updates via **WebSocket (default)** or **polling (fallback)**, user-selectable. Both push full state each tick (not diffs).

## Important Development Notes

### Backend
- **Session storage is in-memory** (`SimulationService`): restarting the backend clears all simulations. No DB.
- **Backward stepping / reset = deterministic replay**: `service._build_model_at_step` rebuilds from the original params+seed and re-steps forward. Large rewinds are slower than forward steps; relies on a fixed `seed`.
- **All tunable numbers live in `config.py`.** When changing model behavior, change the constant there (and keep it consistent with the paper/doc) rather than inlining values.
- **CORS** is enabled for `http://localhost:5173`; update if the frontend port changes.
- **Hot reload** covers Python files in `app/`; schema/route changes still need a browser refresh.

### Frontend
- `frontend/.env` must set `VITE_API_BASE`. Point it elsewhere if the backend isn't on `localhost:8000`.
- Network graph with animations can be slow at large populations (>5000 users); consider node sampling.

### Extending the simulation
**New metric**: add reporter in `metrics.py` → ensure it's in the `DataCollector` (`build_all_reporters`) → it flows through `/timeseries` automatically → add a `<Line>` in `ChartsPanel`.
**New dark pattern**: add a profile to `DARK_PATTERN_DEFAULTS` + per-type `pattern_sensitivity` range in `config.py` → handle in `patterns.py` → instantiate in `model.__init__` `pattern_flags` → add a `pattern_*` param to the schema + form.
**New network type**: add a branch in `model._build_network` → extend the `network_type` Literal in `schemas/simulation.py` + the form option.

## Related documentation
- `README.md` — full user guide, troubleshooting, roadmap
- `CALIBRATION_PLAN.md` — parameter calibration strategy (literature, survey data, behavioral constraints)
- `VERSION_NOTES.md` — changelog
- `docs/superpowers/{plans,specs}/` — design notes for recent mechanics (reputation-discounted revenue, WOM/trust tuning)
- `paper/` — the thesis this model backs (PDF, Markdown, LaTeX source under `fipu-thesis/`)
- `dark-matters-ABM-COLAB.ipynb` — Colab notebook for running the model

## Running in Docker
Not set up yet. To containerize, add a backend `Dockerfile`, a frontend `Dockerfile` (or multi-stage build), and a `docker-compose.yml`. Docker is not required for local development.
