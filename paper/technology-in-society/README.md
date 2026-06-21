# Technology in Society — submission package

Everything needed to submit *"Simulating the Long-Term Impact of Dark Patterns on User Trust: A Network-Based Agent-Based Model"* to the Elsevier journal **Technology in Society** (ISSN 0160-791X), together with a full, journal-grade **replication package** (data + code) that re-generates every result from the simulation.

**Authors:** Dejana Pivac (`dpivac@fipu.hr`), Darko Etinger (`darko.etinger@unipu.hr`) — Faculty of Informatics, Juraj Dobrila University of Pula, Pula, Croatia.

## Folder structure

| Folder | Contents |
|--------|----------|
| `manuscript/` | The LaTeX manuscript (Elsevier **els-cas**, single column): `main.tex`, `references.bib` (author–date), `declarations.tex`, `assemble.py` (copies generated tables/figures/macros in), plus `tables/`, `figures/`, `paper_macros.tex` after assembly. |
| `supplementary/` | `ODD-protocol.tex` — the full ODD-2020 (Grimm et al. 2020) model description, a standalone compilable LaTeX document for the Supplementary Material. |
| `replication-package/` | `reproduce.py` (single command → all tables + figures), pinned environment (`requirements.lock`, `requirements.txt`, `environment.yml`, `Dockerfile`), generated `data/` and `figures/`, `README.md`, `REPRODUCTION.md`, `data-dictionary.md`, `LICENSE` (MIT), `LICENSE-docs.md` (CC-BY-4.0), `CITATION.cff`, `.zenodo.json`, `availability-statement.md`. |

## How everything fits together (reproducibility)

No number is hand-typed in the manuscript. `reproduce.py` runs the seven scenarios over 100 seeds, writes the tables as `.tex`, every inline figure as a `\newcommand` in `paper_macros.tex`, and the figures as vector PDFs. `manuscript/main.tex` `\input`s those, so the paper is a faithful, regenerable view of the simulation. The model itself is the live code in `backend/app/simulation/` (single source of truth) — the package imports it, it is not a fork.

To rebuild from scratch:
```bash
cd replication-package
pip install -r requirements.lock      # Python 3.12.5
python reproduce.py                   # ~30 min → data/ + figures/
cd ../manuscript
python assemble.py                    # copy macros/tables/figures into manuscript/
# then build main.tex with pdfLaTeX + BibTeX (e.g. on Overleaf)
```

## Building the manuscript (no local TeX needed)

The manuscript targets the official Elsevier **els-cas** class (`cas-sc.cls`), which is not vendored here. Easiest path:
1. Create a new Overleaf project from the **"Elsevier CAS (single column)"** template (or download `els-cas-templates` from CTAN: <https://ctan.org/pkg/els-cas-templates>).
2. Upload `manuscript/main.tex`, `references.bib`, `paper_macros.tex`, and the `tables/` and `figures/` folders (produced by `assemble.py`).
3. Compile with pdfLaTeX + BibTeX. Reference style is Chicago author–date (`cas-model2-names`); to switch to numbered, change `\bibliographystyle` to `cas-model1-num`.

## Submission checklist (Technology in Society / Elsevier)

Done in this package:
- [x] Full-length **Article** (target 5,000–10,000 words).
- [x] Abstract ~200 words (limit 150–250); ≤6 keywords.
- [x] **Highlights** (3–5 bullets ≤85 chars) — in `main.tex` `\begin{highlights}`.
- [x] Single-column manuscript with editable source (`.tex`).
- [x] CRediT statement, Declaration of competing interest, Funding, **Data Availability Statement** (Elsevier Option C), GenAI declaration — `manuscript/declarations.tex` + `main.tex`.
- [x] Replication package (code + data) with pinned env, determinism, ODD protocol.

Author TODO before submitting (decisions/placeholders to fill):
- [ ] **Confirm the reference style** with the handling editor: the journal's author-guide PDF says Chicago author–date (built here), but Elsevier tooling assumes numbered `[1]`. One-line switch if needed.
- [ ] **Deposit** the replication package on **Zenodo** (GitHub release → DOI) and optionally the **CoMSES** model library; then replace `<ZENODO_DOI>`, `<GITHUB_URL>`, and the CoMSES URL in `main.tex`/`declarations.tex`/`README.md`/`CITATION.cff`/`.zenodo.json`.
- [ ] Add each author's **ORCID** (`CITATION.cff`, `.zenodo.json`, optionally the title page).
- [ ] Review the **CRediT role assignment** in `declarations.tex` (currently a plausible default).
- [ ] Confirm the **GenAI** declaration wording in `declarations.tex`.
- [ ] Prepare a **cover letter**; note the journal uses **double-anonymized** review → also produce a blinded manuscript + separate title page in Editorial Manager.
- [ ] Export figures to the resolution/format Elsevier requests if asked (vector PDF is provided).

See `replication-package/README.md` and `REPRODUCTION.md` for the reproduction details, and `supplementary/ODD-protocol.tex` for the formal model description.
