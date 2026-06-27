# Data and Code Availability Statement

This is the plain-text Data and Code Availability Statement for the manuscript.
It mirrors the "Data availability" declaration in the manuscript and is provided
here for direct copy-paste into Elsevier Editorial Manager (Technology in
Society, Elsevier data policy Option C).

---

The complete replication package — the agent-based model source code, the
single-command reproduction harness (`reproduce.py`), a pinned computational
environment (`requirements.txt`, `requirements.lock`, `environment.yml`,
`Dockerfile`), and all generated data products (per-run results, aggregate
tables, per-step time series, tipping-point and sensitivity summaries, and
figures) — is openly available. The archived, citable version is deposited on
Zenodo at <ZENODO_DOI>, and the development repository is hosted on GitHub at
<GITHUB_URL>. Running `reproduce.py` in the pinned environment regenerates every
table and figure reported in this article. Each run is fully determined by its
(scenario, seed) pair, so results reproduce exactly on the same code and
dependency versions.

Source code is released under the MIT License. Documentation, the ODD (Overview,
Design concepts, Details) protocol description, figures, and the generated data
are released under the Creative Commons Attribution 4.0 International
(CC BY 4.0) License.

---

## Before submission — fill in these placeholders

- `<ZENODO_DOI>` — the DOI minted when you publish the GitHub release to
  Zenodo (e.g. `https://doi.org/10.5281/zenodo.XXXXXXX`).
- `<GITHUB_URL>` — the public repository URL
  (e.g. `https://github.com/dejanapivac/dark-matters-ABM`).

Optional but recommended: also deposit the model in the CoMSES Net
Computational Model Library (https://www.comses.net/) for a peer-reviewed model
badge and a discipline-specific DOI, and add that link here as well.
