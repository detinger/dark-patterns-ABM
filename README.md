# Dark Patterns ABM simulation web app

A full-stack project for exploring **agent-based simulations of dark patterns and long-term user trust erosion**.

This repository gives you a clean foundation for a research prototype where:

- **Mesa** handles the simulation model in Python
- **FastAPI** exposes the simulation through REST endpoints plus a live WebSocket stream
- **React + TypeScript + Vite** provide a modern dashboard UI
- **Mesa + SolaraViz** are available as an optional original Mesa frontend
- **Recharts** renders time-series charts
- **react-force-graph** visualizes the full user network plus the platform node

The project is intentionally designed as a **starter**: it already runs, but it also leaves room for substantial research and engineering improvements.

---

## What is included

### Backend
- Mesa-based ABM for trust erosion under dark patterns
- Beta-distributed user trait sampling for bounded behavioral parameters
- In-memory simulation session manager
- Formal tipping-point detection with persistent trigger rules
- FastAPI endpoints for:
  - creating simulations
  - stepping simulations forward and backward
  - resetting simulations
  - fetching current state
  - fetching time-series results
  - exporting run data to CSV
  - deleting simulations
- Batch experiment runner scaffold

### Frontend
- Modern React dashboard
- Simulation creation form
- KPI cards
- Tipping-point status panel
- Time-series charts
- Full-network visualization with platform node, live legend, colored trust states, and always-on animated interaction effects
- Live run mode with speed slider and selectable `WebSocket` or `Polling` transport
- CSV export button for the active simulation
- Session list for loading/deleting in-memory runs

---

## Project structure

```text
.
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── routes.py
│   │   ├── schemas/
│   │   │   └── simulation.py
│   │   ├── simulation/
│   │   │   ├── agents.py
│   │   │   ├── config.py
│   │   │   ├── metrics.py
│   │   │   ├── model.py
│   │   │   └── service.py
│   │   ├── experiments.py
│   │   ├── main.py
│   │   └── solara_app.py
│   └── requirements.txt
├── frontend/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── hooks/
│   │   ├── lib/
│   │   ├── types/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── styles.css
│   ├── .env.example
│   ├── index.html
│   ├── package.json
│   ├── tsconfig.json
│   ├── tsconfig.node.json
│   └── vite.config.ts
├── dark-matters-ABM-COLAB.py
├── CALIBRATION_PLAN.md
├── .gitignore
└── README.md
```

---

## Architecture

```text
Option A: React + TypeScript -> FastAPI -> Mesa model
Option B: Mesa + SolaraViz -> Mesa model
```

### Responsibilities by layer

#### Mesa / simulation layer
Responsible for:
- agents
- state transitions
- network effects
- trust updates
- churn logic
- revenue and reputation proxies
- tipping-point detection
- time-series collection

#### FastAPI layer
Responsible for:
- creating simulation sessions
- storing in-memory model instances
- stepping or resetting simulations
- serializing state for the UI
- streaming live ticks to the dashboard over WebSocket

#### React layer
Responsible for:
- parameter input
- scenario control
- visualizing metrics
- live stepping controls
- CSV export
- visualizing full network state and animated interaction events
- interacting with the API

---

## Domain model overview

### UserAgent
Represents one application user with traits such as:
- digital literacy
- manipulation sensitivity
- social activity
- complaint propensity
- switching cost
- trust baseline

Dynamic state includes:
- current trust
- perceived fairness
- cumulative harm
- negative WOM
- active vs churned status

### PlatformAgent
Represents the platform/provider with variables such as:
- dark pattern intensity
- support quality
- adaptive strategy flag
- reputation
- short-term revenue
- long-term revenue

### Environment
The simulation uses a user network rather than a 2D grid. The backend currently supports:
- `small_world`
- `scale_free`
- `random`

The dashboard now visualizes the full user graph, includes the platform as a distinct graph node, and keeps a stable per-simulation layout so interaction animations can play without node positions shifting on every tick.

---

## Main simulation mechanics

Each simulation step roughly follows this order:

1. **Direct exposure**
   - users may encounter active dark patterns
2. **Trust and harm update**
   - trust declines, harm accumulates
3. **Social diffusion**
   - negative word-of-mouth spreads through the network
4. **Recovery**
   - support quality can partially repair trust
5. **Churn decision**
   - users may leave based on trust, harm, WOM, switching cost
6. **Platform update**
   - reputation and revenue proxies are updated
7. **Optional adaptation**
   - platform may reduce dark pattern intensity if outcomes worsen

### Formal tipping-point detection

The current implementation records a tipping point only when a rule remains true for **3 consecutive steps**.

- **Trust Collapse**
  - `mean_trust <= 0.50`
- **Social Contagion**
  - `negative_wom_rate >= 0.22`
- **Churn Cascade**
  - `cumulative_churn >= 0.35`
- **Extractive Divergence**
  - revenue gap is at least `20%` of short-term revenue while `cumulative_churn >= 0.15`

---

## API overview

Base URL:

```text
http://localhost:8000/api
```

### Health
`GET /health`

### Simulations
`GET /simulations`

Returns all in-memory sessions currently stored in the backend process.

### Create simulation
`POST /simulations`

Example request body:

```json
{
  "num_users": 500,
  "network_type": "small_world",
  "avg_degree": 8,
  "rewire_prob": 0.08,
  "max_steps": 104,
  "seed": 42,
  "dark_pattern_intensity": 0.4,
  "pattern_forced_trial": true,
  "pattern_hard_cancel": true,
  "pattern_drip_pricing": true,
  "customer_support_quality": 0.3,
  "adaptive_platform": false,
  "social_influence_strength": 0.18,
  "review_visibility": 0.35
}
```

### Get simulation state
`GET /simulations/{simulation_id}`

Returns:
- parameters
- current step
- latest metrics
- full network snapshot
- recent interaction events for animated network rendering
- platform state
- tipping-point status

### Step simulation
`POST /simulations/{simulation_id}/step`

Request body:

```json
{ "count": 10 }
```

This advances the model by the requested number of steps or until `max_steps` is reached.

Negative values are also supported, which rewinds the simulation deterministically by rebuilding from the original seed and replaying to the target step.

### Reset simulation
`POST /simulations/{simulation_id}/reset`

Resets the existing session using its original parameters.

### Get time series
`GET /simulations/{simulation_id}/timeseries`

Returns a list of data points from Mesa `DataCollector`.

### Live simulation stream
`WS /simulations/{simulation_id}/live?interval_ms=280`

Streams live updates for the selected simulation. Each message includes:
- event type such as `snapshot`, `tick`, `complete`, or `error`
- current simulation state
- full time-series data
- updated simulation list metadata

The React dashboard uses this endpoint when `WebSocket` is selected as the live transport. `Polling` remains available as a fallback mode.

### Export CSV
`GET /simulations/{simulation_id}/export.csv`

Downloads a CSV containing:
- one row per step
- all collected model metrics
- tipping-point trigger flags and trigger steps
- the full parameter set repeated on each row for analysis portability

### Delete simulation
`DELETE /simulations/{simulation_id}`

Removes the simulation from in-memory storage.

---

## Running the project

### Prerequisites

You should have installed:
- **Python 3.11+** recommended
- **Node.js 20+** recommended for the React dashboard
- **npm** for the React dashboard

---

## Quick Local Scripts

If you want the fastest local setup/run path from the repository root, use:

```bash
./setup-local.sh
./run-local.sh
```

What they do:

- `./setup-local.sh`
  - creates `backend/.venv`
  - installs backend dependencies
  - installs frontend dependencies
  - creates `frontend/.env` from `.env.example` if needed
  - sets `VITE_API_BASE=http://localhost:8000/api`
- `./run-local.sh`
  - starts the backend with `python -m app.dev_server`
  - starts the frontend with `npm run dev`
  - stops both services when you press `Ctrl+C`

---

## 1. Manual setup

Open a terminal in `backend/`.

### Create and activate a virtual environment

#### macOS / Linux
```bash
python -m venv .venv
source .venv/bin/activate
```

#### Windows PowerShell
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Install dependencies

```bash
pip install -r requirements.txt
```

---

## 2. Choose a frontend

You can now run the project in either of these ways:

- **React dashboard + FastAPI** if you want the existing custom web app
- **Mesa SolaraViz** if you want the original Mesa-style interactive frontend

### Option A. Run the existing React dashboard

#### Run the API

From the `backend/` folder:

```bash
python -m app.dev_server
```

The backend should be available at:

```text
http://localhost:8000
```

Interactive docs will be available at:

```text
http://localhost:8000/docs
```

#### Start the React frontend

Open a second terminal in `frontend/`.

### Install dependencies

```bash
npm install
```

### Optional environment file

Copy the example file if you want to customize the API base URL.

#### macOS / Linux
```bash
cp .env.example .env
```

#### Windows PowerShell
```powershell
Copy-Item .env.example .env
```

### Start the frontend

```bash
npm run dev
```

The React app should be available at:

```text
http://localhost:5173
```

### Option B. Run the Mesa SolaraViz frontend

From the `backend/` folder:

```bash
solara run app/solara_app.py --production --port 8765
```

The Mesa frontend should be available at:

```text
http://localhost:8765
```

This mode reuses the same `DarkPatternTrustModel`, keeps the platform visible in the network view, and gives you Mesa's built-in play, pause, step, and reset controls without needing the React app or FastAPI server.

---

## First run workflow

### React dashboard path

1. Start the backend
2. Start the frontend
3. Open the dashboard in your browser
4. Create a simulation using the left-hand form
5. Click:
   - `Step -1`
   - `Step +1`
   - `Run -10`
   - `Run +10`
   - `Run Live`
6. Choose the live transport in the control panel:
   - `WebSocket` for the default low-overhead live stream
   - `Polling` if you want to compare behavior or need a simpler fallback

### Mesa SolaraViz path

1. Start the Solara app
2. Open `http://localhost:8765`
3. Adjust parameters in the Mesa controls
4. Use `Step`, `Play/Pause`, and `Reset`
5. Inspect the network overview, summary tables, and Mesa plots

---

## Running batch experiments

The repository includes a starter batch runner in:

```text
backend/app/experiments.py
```

Before running batch experiments, make sure the backend virtual environment exists and the Python dependencies are installed. Otherwise you may see errors such as `ModuleNotFoundError: No module named 'pandas'`.

Run it from the `backend/` folder:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m app.experiments
```

If the virtual environment is already set up, you only need:

```bash
cd backend
source .venv/bin/activate
python -m app.experiments
```

You can also run it without activating the environment:

```bash
cd backend
.venv/bin/python -m app.experiments
```

The script writes results to:

```text
backend/results/batch_results.csv
```

---

## Default parameters

### Population and network
- `num_users = 500`
- `network_type = small_world`
- `avg_degree = 8`
- `rewire_prob = 0.08`
- `max_steps = 104`

### Platform
- `dark_pattern_intensity = 0.40`
- `pattern_forced_trial = true`
- `pattern_hard_cancel = true`
- `pattern_drip_pricing = true`
- `customer_support_quality = 0.30`
- `adaptive_platform = false`

### Social diffusion
- `social_influence_strength = 0.18`
- `review_visibility = 0.35`

---

## Suggested development roadmap

### 1. Strengthen the scientific model
Good next steps:
- replace bounded normal sampling with proper Beta distributions [DONE]
- calibrate parameters from literature or survey data [PLAN ADDED]
- formalize tipping point detection [DONE]
- store agent-type segments explicitly
- improve revenue model

### 2. Improve backend architecture
Possible upgrades:
- add persistent storage for simulation metadata
- save results to Postgres or Redis (I don't need that for now)
- add background jobs for long experiments
- add authentication if needed

### 3. Improve frontend UX
Possible upgrades:
- scenario comparison view
- multiple saved charts
- export to CSV/JSON/PNG [CSV DONE]
- parameter presets
- richer network controls
- dark mode and polished layout system [DONE]

### 4. Improve research workflows
Possible upgrades:
- notebook analysis pipeline [DONE]
- automated report generation [DONE, csv/colab]
- sensitivity analysis dashboards
- experiment registry

## Calibration reference

For a parameter-by-parameter calibration plan linked to literature, surveys, audits, and behavioral data, see:

- `CALIBRATION_PLAN.md`

---

## Known limitations


Current limitations include:
- simulation sessions are stored **in memory only**
- restarting the backend clears all sessions
- backward stepping works by deterministic replay, so large rewinds are more computationally expensive than forward steps
- metrics are illustrative and not empirically calibrated
- there is no authentication or persistence layer
- long experiment execution is synchronous
- live WebSocket updates still send full state payloads on each tick rather than smaller diffs
- the full animated network can become visually and computationally heavy at large population sizes


---

## Suggested thesis framing

This project supports a framing like:

> A stochastic, network-based agent-based simulation of long-term trust erosion caused by dark patterns in digital applications, exposed through a modern web interface for scenario exploration and comparative analysis.

That framing keeps:
- **Mesa** as the scientific model core
- **FastAPI** as the delivery layer
- **React** as the presentation layer

---

## Troubleshooting

### Backend import errors
Make sure you are in the `backend/` folder when starting Uvicorn:

```bash
python -m app.dev_server
```

### CORS errors in the browser
Make sure:
- backend runs on `http://localhost:8000`
- frontend runs on `http://localhost:5173`
- you did not change ports without updating CORS or `VITE_API_BASE`

### Frontend cannot reach API
Check:
- backend is running
- `frontend/.env` has the correct `VITE_API_BASE`
- browser console and FastAPI logs for errors

### WebSocket live mode disconnects
Check:
- backend is running on `http://localhost:8000`
- the browser can reach `ws://localhost:8000/api/...`
- you can switch the live transport to `Polling` as a fallback if the socket is interrupted

### Simulation disappears
That is expected if the backend restarts because sessions are stored in memory.

### Full graph feels heavy
The dashboard now renders the full network plus a platform node and animated interaction events. Large populations can make the browser graph slower, especially near the upper end of the allowed user count.

---

## Deploying on Railway

This repository is an isolated monorepo, so deploy the frontend and backend as two Railway services connected to the same GitHub repository.

### 1. Create the services

Create two services named `backend` and `frontend`. For each service, open **Settings** and configure:

| Service | Root Directory | Railway Config File | Watch Path |
| --- | --- | --- | --- |
| `backend` | `/backend` | `/backend/railway.toml` | `/backend/**` |
| `frontend` | `/frontend` | `/frontend/railway.toml` | `/frontend/**` |

The config-file paths are repository-absolute because Railway does not resolve them relative to the service Root Directory.

### 2. Generate public domains

Under **Settings -> Networking**, generate a Railway domain for both services.

### 3. Connect the services

Add this runtime variable to the `frontend` service:

```env
API_UPSTREAM=https://${{backend.RAILWAY_PUBLIC_DOMAIN}}
```

Enter the value without surrounding quotes or a trailing `/api`. The `backend` part of the reference must exactly match the Railway backend service name. If the reference does not resolve, use the generated backend origin directly:

```env
API_UPSTREAM=https://your-backend.up.railway.app
```

The deployed frontend sends browser requests to its own `/api` path, and Caddy forwards them to `API_UPSTREAM`. This avoids cross-origin browser requests and allows the upstream to be changed at runtime. Remove any old `VITE_API_BASE` variable from the frontend service, then deploy the staged variable change and redeploy the frontend.

### 4. Verify the deployment

- Backend health: `https://<backend-domain>/api/health`
- Backend API docs: `https://<backend-domain>/docs`
- Frontend: `https://<frontend-domain>/`
- Proxied health check: `https://<frontend-domain>/api/health`

The backend Railway config starts Uvicorn on Railway's injected `PORT`. The frontend Dockerfile builds the Vite app and serves it with Caddy on the same injected port.

---

## Recommended next files to add

If you want to continue developing this seriously, the next high-value additions are:

- `backend/app/simulation/scenarios.py`
- `backend/app/simulation/serialization.py`
- `backend/app/analysis/`
- `backend/tests/`
- `frontend/src/pages/ComparisonPage.tsx`
- `frontend/src/components/ScenarioPresetCards.tsx`
- `frontend/src/components/ExportButtons.tsx`

---

## Final note

The simulation is already separated cleanly enough that you can evolve it in three directions at once:
- scientific model refinement
- API hardening
- UI modernization
