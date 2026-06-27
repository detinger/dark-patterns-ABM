# Reproduction Protocol

This document is the detailed protocol for reproducing every numerical result, table, and figure in
the manuscript *"Simulating the Long-Term Impact of Dark Patterns on User Trust: A Network-Based
Agent-Based Model"* (submitted to *Technology in Society*). For a high-level overview and quick-start commands, see `README.md`.

The entire reproduction is driven by **one script**, `reproduce.py`, which imports the simulation
model from the repository's `backend/app/simulation/` package (the single source of truth) and
writes all artifacts into this package's `data/` and `figures/` directories.

---

## 1. Overview and expected runtime

`reproduce.py` runs the **seven scenarios** reported in the paper, each replicated over a set of
random seeds, then aggregates the per-run results into the manuscript tables, runs a local
sensitivity sweep, and renders the figures.

| Step | What it does | Approx. time |
|------|--------------|--------------|
| Single model run | `N = 500`, 312 steps (1 step = 1 week ≈ 6 years) | ≈ 1.4 s |
| 7 scenarios × 100 seeds | 700 full runs (the main results) | ≈ 16–18 min |
| Sensitivity analysis | 3 parameters × grid × 30 seeds ≈ 630 runs | ≈ 12–14 min |
| Tables, macros, figures | aggregation + 8 vector PDFs | < 30 s |
| **Full `python reproduce.py`** | **everything above** | **≈ 30 min** |
| `python reproduce.py --quick` | 5 seeds, no sensitivity (smoke test) | < 1 min |

Timings are for a single CPU core on a typical modern laptop; the run is single-threaded and CPU-
bound, so wall-clock scales roughly linearly with the replicate count.

---

## 2. Computational requirements

- **Operating system:** any OS with Python 3.12 (developed and published on Windows; the Docker
  image uses `python:3.12.5-slim` Linux). No OS-specific code.
- **Python:** 3.12.5 (the exact version behind the published numbers).
- **Dependencies (pinned):** `mesa==3.5.1`, `networkx==3.6.1`, `numpy==2.4.6`, `pandas==3.0.3`,
  `matplotlib==3.11.0`. These five are sufficient for `reproduce.py`. The full, fully-reconstructable
  environment is in `requirements.lock` (a `pip freeze`); `requirements.txt` lists the minimal set;
  `environment.yml` is the conda equivalent.
- **Hardware:** no GPU required. A few hundred MB of free disk is enough — the bulky outputs are the
  700 compressed per-run CSVs in `data/raw/` (skip them with `--no-raw` if disk is tight).
- **Memory:** modest (well under 2 GB); one model and one DataFrame are held in memory at a time.
- **Network:** none required at run time (only for installing dependencies).

---

## 3. Step-by-step instructions

All commands are run **from this `replication-package/` directory** unless noted. Pick one of the
three environments below (see `README.md` for full quick-start), then run the reproduction.

### 3.1 Create the environment

```bash
# pip (exact, recommended)
python3.12 -m venv .venv
source .venv/bin/activate           # Windows: .venv\Scripts\activate
pip install -r requirements.lock

# --- or conda ---
conda env create -f environment.yml
conda activate dark-patterns-abm
```

### 3.2 Smoke test (always do this first)

```bash
python reproduce.py --quick
```

This runs 5 seeds per scenario and skips the sensitivity sweep — it exercises the entire pipeline
(simulation → per-run CSV → tables → macros → figures) in under a minute and confirms the
environment is wired correctly. Note that `--quick` overwrites the processed tables/figures with
low-replicate versions, so re-run the full command afterwards to restore the published artifacts.

### 3.3 Full reproduction

```bash
python reproduce.py
```

This reproduces the published results exactly: 7 scenarios × 100 seeds (seeds 0–99), the sensitivity
analysis (30 seeds per grid point), all tables (`.csv` + `.tex`), `paper_macros.tex`, the figures,
and `run_manifest.json`.

### 3.4 Useful flags

| Flag | Effect |
|------|--------|
| `--quick` | 5 replicates, no sensitivity (smoke test). |
| `--replicates N` | Use *N* seeds per scenario instead of 100. |
| `--sensitivity-replicates N` | Seeds per sensitivity grid point (default 30). |
| `--seed-base K` | Start seeds at *K* (seeds `K … K+replicates-1`); default 0. |
| `--no-figures` | Skip figure rendering. |
| `--no-sensitivity` | Skip the sensitivity sweep. |
| `--no-raw` | Do not write the bulky `data/raw/` per-run CSVs. |
| `--macros-only` | Regenerate tables + `paper_macros.tex` from an existing `per_run_final.csv` (no simulation). |

### 3.5 Docker (OS-independent alternative)

Build from the **repository root** so `backend/` is in the build context:

```bash
docker build -f paper/technology-in-society/replication-package/Dockerfile -t dark-patterns-abm .
docker run --rm \
  -v "$(pwd)/paper/technology-in-society/replication-package/data:/app/paper/technology-in-society/replication-package/data" \
  -v "$(pwd)/paper/technology-in-society/replication-package/figures:/app/paper/technology-in-society/replication-package/figures" \
  dark-patterns-abm
```

---

## 4. Controlled randomness (determinism)

**Every run is fully determined by its `(scenario, seed)` pair.** Reproducibility relies on the
following facts, all verifiable in the model source:

- The model routes **all** stochasticity through a **single seeded RNG**. The constructor calls
  `super().__init__(rng=seed)` (Mesa 3.x), which seeds Mesa's `self.random` (a Python
  `random.Random`). Every random draw in the model and agents — user-type assignment
  (`rng.choices`), trait sampling (`beta_sample` via `rng.betavariate`), network construction
  (the seed passed to NetworkX's `watts_strogatz_graph` / `barabasi_albert_graph` /
  `erdos_renyi_graph` is itself drawn from `self.random`), initial reputation
  (`self.random.uniform`), exposure/detection/harm/WOM/churn decisions, and natural attrition — uses
  this one generator (`self.random` / `self.model.random`). Any numpy draws are derived from the
  same seeded stream. There is **no other source of randomness** (no wall-clock seeding, no
  unseeded `numpy.random`, no hashing of unordered structures affecting results).
- The reproduction harness uses **seeds 0–99** for the main scenarios (`--seed-base 0`,
  `--replicates 100`) and seeds 0–29 for each sensitivity grid point. Seeds are recorded in
  `data/processed/run_manifest.json`.
- Given the **same model code and the same pinned dependency versions** (`requirements.lock`,
  echoed in `run_manifest.json` under `versions`), re-running `reproduce.py` produces **identical
  output**. Cross-version or cross-platform numerical drift is possible if dependency versions
  differ (especially numpy/NetworkX); always reproduce against `requirements.lock`.
- **Integrity check:** `checksums.sha256` lists the SHA-256 of every generated artifact. After a
  full run on the pinned environment, verify with:

  ```bash
  sha256sum -c checksums.sha256          # Linux/macOS
  # Windows (PowerShell): Get-FileHash <file> -Algorithm SHA256
  ```

  Matching checksums confirm a bit-for-bit reproduction. (`checksums.sha256` is generated from the
  published run and shipped with the package.)

---

## 5. Mapping of manuscript outputs to reproduction artifacts

Each table and figure in the manuscript is produced by exactly one `reproduce.py` output file. All
files are written under `data/processed/` (tables, macros, timeseries) or `figures/` (PDFs).

### Tables

| Manuscript | Generated file(s) | Built by | Scenarios | Key metrics |
|------------|-------------------|----------|-----------|-------------|
| **Table I** — outcomes by intensity | `data/processed/table1_intensity.tex` (+ `.csv`) | `build_table1()` | control, low (0.20), medium (0.40), high (0.80) | cumulative churn, mean trust (all), mean harm, platform reputation, cumulative revenue, opportunity cost, tipping points triggered |
| **Table II** — churn by user type | `data/processed/table2_churn_by_type.tex` (+ `.csv`) | `build_table2()` | control, low, medium, high | per-type churn count and % of type (skeptic / naive / activist) |
| **Table III** — single-pattern impact | `data/processed/table3_per_pattern.tex` (+ `.csv`) | `build_table3()` | forced_trial_only, hard_cancel_only, drip_pricing_only (all at intensity 0.50) | cumulative churn, mean trust (all), trust-collapse step, tipping points triggered |
| Inline numbers in prose | `data/processed/paper_macros.tex` | `build_paper_macros()` | all 7 | every point estimate cited in the text, as `\newcommand` macros the manuscript `\input`s |

### Figures

| Manuscript figure | Generated file | Source data | Scenarios | Metric |
|-------------------|----------------|-------------|-----------|--------|
| Trust trajectories | `figures/fig_trust_by_intensity.pdf` | `timeseries/{control,low,medium,high}_intensity.csv` | 4 intensity | `mean_trust_all` (mean + 95 % band) |
| Cumulative churn | `figures/fig_churn_by_intensity.pdf` | same timeseries | 4 intensity | `cumulative_churn` |
| Social contagion | `figures/fig_negwom_by_intensity.pdf` | same timeseries | 4 intensity | `negative_wom_rate` |
| Platform reputation | `figures/fig_reputation_by_intensity.pdf` | same timeseries | 4 intensity | `platform_reputation` |
| Cumulative revenue | `figures/fig_revenue_by_intensity.pdf` | same timeseries | 4 intensity | `cumulative_revenue` |
| Churn by user type | `figures/fig_churn_by_type.pdf` | `per_run_final.csv` | 4 intensity | final per-type churn % (grouped bars) |
| Single-pattern impact | `figures/fig_per_pattern.pdf` | `per_run_final.csv` | 3 pattern-only | final cumulative churn + mean trust |
| Sensitivity analysis | `figures/fig_sensitivity.pdf` | `sensitivity.csv` | medium baseline | churn + trust vs. intensity / social influence / support quality |

The seven scenarios are defined in `backend/app/simulation/config.py` (`SCENARIOS`):
`control` (intensity 0.0), `low_intensity` (0.20), `medium_intensity` (0.40), `high_intensity`
(0.80), and the three single-pattern conditions `forced_trial_only`, `hard_cancel_only`,
`drip_pricing_only` (each at intensity 0.50).

---

## 6. List of tables and figures with source data files

| Output | Type | Immediate source file |
|--------|------|-----------------------|
| Table I | LaTeX/CSV | `data/processed/per_run_final.csv` → `table1_intensity.{tex,csv}` |
| Table II | LaTeX/CSV | `data/processed/per_run_final.csv` → `table2_churn_by_type.{tex,csv}` |
| Table III | LaTeX/CSV | `data/processed/per_run_final.csv` → `table3_per_pattern.{tex,csv}` |
| Inline macros | LaTeX | `data/processed/per_run_final.csv` + `tipping_points.csv` → `paper_macros.tex` |
| Tipping-point summary | CSV | `data/processed/tipping_points.csv` |
| Fig. trust / churn / negwom / reputation / revenue by intensity | PDF | `data/processed/timeseries/{control,low_intensity,medium_intensity,high_intensity}.csv` |
| Fig. churn by user type | PDF | `data/processed/per_run_final.csv` |
| Fig. per-pattern impact | PDF | `data/processed/per_run_final.csv` |
| Fig. sensitivity | PDF | `data/processed/sensitivity.csv` |

The timeseries CSVs and `per_run_final.csv` are themselves derived from the per-run raw outputs in
`data/raw/<scenario>/seed_<NN>.csv.gz`, which preserve the full per-step output of every run.
Every column in these files is documented in `data-dictionary.md`.

---

## 7. Notes and caveats

- **Time semantics.** One simulation step = one week; the reporting horizon is 312 steps ≈ 6 years
  (`DEFAULT_MAX_STEPS = 312`, `DEFAULT_NUM_AGENTS = 500` in `config.py`).
- **Confidence intervals.** Tables and figure bands report mean ± 95 % CI using a normal
  approximation (`CI_Z = 1.96`); this is appropriate at *n* = 100 seeds but is wider/less reliable
  in low-replicate modes such as `--quick`.
- **"Medium" intensity is 0.40.** The canonical medium scenario reported in Table I uses
  `dark_pattern_intensity = 0.40` (see the comment on `SCENARIOS["medium_intensity"]` in
  `config.py`). This is also the baseline for the local sensitivity analysis.
- **`reputation_range` is defined but not consumed by the model.** Each entry in `SCENARIOS`
  carries a `reputation_range` key, but `run_scenario()` does not forward it and the model does not
  accept it. Initial platform reputation is instead drawn from the global
  `DEFAULT_REPUTATION_RANGE = (50, 70)` via `self.random.uniform(...)` for **all** scenarios. The
  per-scenario `reputation_range` values are therefore inert metadata and do not affect any reported
  result.
- **Post-hoc calibration.** The model constants in `config.py` were tuned relative to an earlier
  draft so that the qualitative regime boundaries (trust collapse, churn cascade, extractive
  divergence) fall in plausible ranges; the calibration rationale is documented in the repository's
  `CALIBRATION_PLAN.md`. The numbers reported in the manuscript are the deterministic output of the
  **current** constants, regenerated by this package — the prose in earlier drafts may cite stale
  values, which `paper_macros.tex` supersedes.
- **`--quick` overwrites published artifacts.** Because `--quick` writes to the same processed
  paths, re-run the full `python reproduce.py` to restore the 100-seed tables and figures before
  building the manuscript.
- **Determinism is environment-sensitive.** Identical output is guaranteed only against the pinned
  dependency versions in `requirements.lock`; reproduce in that environment (or via the Docker
  image) before comparing against `checksums.sha256`.
