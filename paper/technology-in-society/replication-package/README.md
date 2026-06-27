# Replication Package — Simulating the Long-Term Impact of Dark Patterns on User Trust: A Network-Based Agent-Based Model

**Authors:** Dejana Pivac (<dpivac@fipu.hr>) and Darko Etinger (<darko.etinger@unipu.hr>)
Faculty of Informatics, Juraj Dobrila University of Pula, Pula, Croatia

This is the complete replication package for the manuscript submitted to *Technology in Society*
(Elsevier, ISSN 0160-791X). It contains the agent-based model (ABM), the single reproduction
harness `reproduce.py`, the pinned computational environment, and the generated data and figures.
Running one command regenerates **every table and figure** in the paper from the model source.

---

## Overview

The study uses an agent-based model to examine how *dark patterns* — manipulative interface
designs such as forced trials, obstructed cancellation, and drip pricing — erode user trust in a
digital platform over time, and how that trust erosion propagates through a social network into
churn, negative word-of-mouth, reputation loss, and the platform's own long-run revenue. The model
simulates `N = 500` heterogeneous users (three behavioural types: skeptic, naive, activist)
connected on a small-world network over `312` weekly steps (≈ 6 years), under a single platform
that applies a tunable dark-pattern intensity. The analysis compares seven scenarios — a clean
control, three intensity levels (0.20 / 0.40 / 0.80), and three single-pattern conditions at
intensity 0.50 — each replicated over **100 random seeds (0–99)**, reporting means with 95 %
confidence intervals (normal approximation, *z* = 1.96).

This package bundles the model code (imported directly from `backend/`, the single source of
truth), the reproduction harness that orchestrates the scenarios and emits the manuscript
artifacts, and the exact dependency versions used to produce the published numbers. No result is
hand-entered in the manuscript: all tables are generated as `.tex`, all inline numbers are emitted
as LaTeX macros (`paper_macros.tex`), and all figures are rendered as vector PDFs.

---

## Directory tree

```
replication-package/
├── README.md                 ← you are here (front door)
├── REPRODUCTION.md           ← detailed step-by-step replication protocol
├── data-dictionary.md        ← column-by-column description of every output file
├── reproduce.py              ← single entry point: regenerates all tables + figures
├── requirements.txt          ← minimal pinned deps (mesa, networkx, numpy, pandas, matplotlib)
├── requirements.lock         ← fully pinned environment (pip freeze, Python 3.12.5)
├── environment.yml           ← conda environment specification
├── Dockerfile                ← containerized, OS-independent reproduction
├── checksums.sha256          ← SHA-256 of every generated artifact (integrity check)
├── data/
│   ├── raw/
│   │   └── <scenario>/seed_<NN>.csv.gz    full per-step output of each individual run
│   └── processed/
│       ├── per_run_final.csv              one row per (scenario, seed): final-step metrics
│       ├── table1_intensity.csv / .tex    Table I  — intensity comparison
│       ├── table2_churn_by_type.csv / .tex Table II — churn by user type
│       ├── table3_per_pattern.csv / .tex  Table III — single-pattern impact at 0.50
│       ├── tipping_points.csv             tipping-point trigger fractions + mean steps
│       ├── sensitivity.csv                local one-at-a-time sensitivity sweep
│       ├── paper_macros.tex               \newcommand for every inline number in the prose
│       ├── run_manifest.json              provenance: versions, seeds, parameters, timing
│       └── timeseries/<scenario>.csv      per-step mean / lo / hi trajectories (figure source)
└── figures/
    ├── fig_trust_by_intensity.pdf
    ├── fig_churn_by_intensity.pdf
    ├── fig_negwom_by_intensity.pdf
    ├── fig_reputation_by_intensity.pdf
    ├── fig_revenue_by_intensity.pdf
    ├── fig_churn_by_type.pdf
    ├── fig_per_pattern.pdf
    └── fig_sensitivity.pdf
```

The model source itself lives in the repository at `backend/app/simulation/` and is imported by
`reproduce.py` (it prepends `../../../backend` to `sys.path`). The replication package is therefore
not a fork of the model — it runs the **same code** the interactive application uses.

---

## Quick start

Run all commands **from this `replication-package/` directory**. The full run takes roughly
**30 minutes** on a typical laptop; a smoke test (`--quick`) finishes in well under a minute. See
`REPRODUCTION.md` for the detailed protocol, flags, and expected runtimes.

### Option 1 — pip + locked environment (recommended for exact reproduction)

```bash
python3.12 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.lock   # exact versions behind the published numbers
python reproduce.py
```

If you only need the runtime dependencies (not the full backend/test/viz stack), the minimal set
in `requirements.txt` is sufficient:

```bash
pip install -r requirements.txt
python reproduce.py
```

### Option 2 — conda

```bash
conda env create -f environment.yml
conda activate dark-patterns-abm
python reproduce.py
```

### Option 3 — Docker (OS-independent)

Build from the **repository root** so the build context includes `backend/`:

```bash
docker build -f paper/technology-in-society/replication-package/Dockerfile -t dark-patterns-abm .

docker run --rm \
  -v "$(pwd)/paper/technology-in-society/replication-package/data:/app/paper/technology-in-society/replication-package/data" \
  -v "$(pwd)/paper/technology-in-society/replication-package/figures:/app/paper/technology-in-society/replication-package/figures" \
  dark-patterns-abm
```

### Smoke test (verify the pipeline in seconds, before committing to the full run)

```bash
python reproduce.py --quick     # 5 seeds, no sensitivity, fast
```

---

## What gets produced

A full `python reproduce.py` run writes, under `data/` and `figures/`:

- **`data/raw/<scenario>/seed_<NN>.csv.gz`** — the complete per-step output of every individual
  run (7 scenarios × 100 seeds = 700 compressed CSVs).
- **`data/processed/per_run_final.csv`** — one row per (scenario, seed) with final-step metrics
  and per-type populations/churn; the single source for all three tables.
- **`data/processed/table1_intensity.{csv,tex}`**, **`table2_churn_by_type.{csv,tex}`**,
  **`table3_per_pattern.{csv,tex}`** — manuscript Tables I, II, III.
- **`data/processed/tipping_points.csv`**, **`sensitivity.csv`**, **`paper_macros.tex`**,
  **`run_manifest.json`**.
- **`data/processed/timeseries/<scenario>.csv`** — per-step mean and 95 % CI band, the source data
  for the trajectory figures.
- **`figures/*.pdf`** — the eight vector figures used in the manuscript.

Each manuscript table and figure maps to exactly one output file; that mapping is documented in
`REPRODUCTION.md`. Every column of every file is described in `data-dictionary.md`.

---

## Documentation pointers

- **`REPRODUCTION.md`** — full computational requirements, exact commands, the determinism /
  controlled-randomness statement, and the table/figure → output-file mapping.
- **`data-dictionary.md`** — per-column description of `per_run_final.csv`, the timeseries files,
  the raw run CSVs, `sensitivity.csv`, and `tipping_points.csv`.

---

## License

- **Code** (`reproduce.py`, the imported `backend/` model): **MIT License**.
- **Data and documentation** (the contents of `data/`, `figures/`, and the `.md` files):
  **Creative Commons Attribution 4.0 International (CC-BY-4.0)**.

You are free to reuse, adapt, and redistribute both, provided you retain the copyright notice
(code) and provide attribution (data/docs).

---

## How to cite

If you use this model, data, or replication package, please cite both the article and the archived
package:

> Pivac, Dejana, and Darko Etinger. 2026. "Simulating the Long-Term Impact of Dark Patterns on
> User Trust: A Network-Based Agent-Based Model." *Technology in Society*. [DOI to be assigned on acceptance].

> Pivac, Dejana, and Darko Etinger. 2026. *Dark Patterns ABM — Replication Package* (version 1.0)
> [Software and data]. Zenodo. https://doi.org/10.5281/zenodo.XXXXXXX  *(placeholder — replaced
> with the Zenodo DOI on deposit; a mirror is also archived at the CoMSES Net Computational Model
> Library)*.

The model description follows the ODD protocol (Grimm et al. 2020, *JASSS* 23(2):7,
https://doi.org/10.18564/jasss.4259).

---

## Data and Code Availability Statement

*(Suitable for the Technology in Society manuscript — Elsevier research-data policy, Option C.)*

The agent-based model, the single reproduction harness (`reproduce.py`), the pinned computational
environment, and all generated data and figures are openly available. The complete replication
package is archived on Zenodo (https://doi.org/10.5281/zenodo.XXXXXXX) and mirrored, with a
peer-reviewed model badge, in the CoMSES Net Computational Model Library
(https://www.comses.net/codebases/XXXXX/). A single command (`python reproduce.py`) regenerates
**every table and figure** reported in the article from the model source; determinism is
guaranteed by a single seeded random-number generator (seeds 0–99) on the pinned dependency
versions recorded in `requirements.lock` and `run_manifest.json`, and verified against
`checksums.sha256`. The code is released under the MIT License and the data and documentation under
CC-BY-4.0. No third-party, proprietary, or personal data were used: all data are synthetic outputs
of the simulation.
