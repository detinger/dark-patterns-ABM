#!/usr/bin/env python3
"""
verify_manuscript.py — static checks on main.tex without compiling LaTeX.

Confirms that every custom result macro, citation key, included figure, and
\\input file referenced by main.tex actually resolves. Run after assemble.py:

    python verify_manuscript.py

Exit code 0 = all checks pass; 1 = at least one missing reference.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAIN = (HERE / "main.tex").read_text(encoding="utf-8")

problems: list[str] = []
ok: list[str] = []

# --- 1. Custom result macros: every \ourMacro used must be \newcommand-defined.
macros_file = HERE / "paper_macros.tex"
defined = set(re.findall(r"\\newcommand\{\\([A-Za-z]+)\}", macros_file.read_text(encoding="utf-8"))) \
    if macros_file.exists() else set()
if not defined:
    problems.append("paper_macros.tex missing or defines no macros (run assemble.py / reproduce.py --macros-only)")

# Custom-macro namespace: prefix + Uppercase, plus the explicit names.
ns = re.compile(r"\\((?:ctrl|low|med|high|forced|hardcancel|drip)[A-Z][A-Za-z]*"
                r"|numReplicates|numAgents|maxSteps|nSkeptic|nNaive|nActivist)\b")
used_macros = set(ns.findall(MAIN))
missing_macros = sorted(used_macros - defined)
if missing_macros:
    problems.append(f"Undefined result macros used in main.tex: {missing_macros}")
else:
    ok.append(f"all {len(used_macros)} result macros defined")

# --- 2. Citation keys: every \cite{...} key must exist in references.bib.
bib = (HERE / "references.bib").read_text(encoding="utf-8")
bib_keys = set(re.findall(r"@\w+\{([^,]+),", bib))
cite_keys: set[str] = set()
for grp in re.findall(r"\\cite[a-z]*\{([^}]*)\}", MAIN):
    cite_keys.update(k.strip() for k in grp.split(","))
missing_cites = sorted(cite_keys - bib_keys)
if missing_cites:
    problems.append(f"Citation keys not in references.bib: {missing_cites}")
else:
    ok.append(f"all {len(cite_keys)} citation keys resolve ({len(bib_keys)} in bib)")

# --- 3. Figures: every \includegraphics target must exist.
for fig in re.findall(r"\\includegraphics(?:\[[^\]]*\])?\{([^}]+)\}", MAIN):
    p = (HERE / fig)
    candidates = [p, p.with_suffix(".pdf"), p.with_suffix(".png")]
    if not any(c.exists() for c in candidates):
        problems.append(f"Figure not found: {fig}")
    else:
        ok.append(f"figure ok: {fig}")

# --- 4. \input files must exist (.tex).
for inc in re.findall(r"\\input\{([^}]+)\}", MAIN):
    p = HERE / inc
    if not (p.exists() or p.with_suffix(".tex").exists()):
        problems.append(f"\\input target not found: {inc}")
    else:
        ok.append(f"input ok: {inc}")

# --- Report ---------------------------------------------------------------
print("Manuscript static verification")
print("=" * 40)
for line in ok:
    print(f"  OK   {line}")
if problems:
    print("\nPROBLEMS:")
    for p in problems:
        print(f"  XX   {p}")
    sys.exit(1)
print("\nAll checks passed.")
