# Licensing of documentation and data

This replication package is released under a dual-licensing scheme.

## Source code — MIT

All **source code** in this package and in the accompanying simulation model
(the Python model under `backend/app/`, `reproduce.py`, and any helper scripts)
is licensed under the **MIT License**. See the [`LICENSE`](./LICENSE) file for
the full terms.

## Documentation, ODD protocol, and generated data — CC BY 4.0

All **non-code material** is licensed under the
**Creative Commons Attribution 4.0 International (CC BY 4.0)** license:

<https://creativecommons.org/licenses/by/4.0/>

This includes, but is not limited to:

- the documentation (`README.md`, `REPRODUCTION.md`, and other `.md` files),
- the ODD (Overview, Design concepts, Details) protocol description of the
  model (cf. Grimm et al. 2020, *JASSS* 23(2):7, DOI 10.18564/jasss.4259),
- the figures (`figures/*.pdf`), and
- the generated data products under `data/processed/` and `data/raw/`
  (per-run CSVs, aggregate tables, time-series, tipping-point summaries,
  sensitivity results, and the run manifest).

### Attribution

When you reuse, adapt, or redistribute any of the CC BY 4.0 material, please
credit the authors as follows:

> Pivac, Dejana, and Darko Etinger. 2026. *Dark Patterns ABM: replication
> package.* Faculty of Informatics, Juraj Dobrila University of Pula, Pula,
> Croatia. <GITHUB_URL> / <ZENODO_DOI>

A citation of the associated journal article and/or the archived deposit (see
[`CITATION.cff`](./CITATION.cff) and [`.zenodo.json`](./.zenodo.json)) also
satisfies the attribution requirement.

---

**Summary:** code is MIT; documentation, the ODD protocol, figures, and the
generated data are CC BY 4.0. Where a file could be considered both, the MIT
License governs executable source and the CC BY 4.0 license governs prose,
figures, and tabular data outputs.
