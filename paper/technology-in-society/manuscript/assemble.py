#!/usr/bin/env python3
"""
assemble.py — copy the simulation-generated artifacts into the manuscript folder
so it is self-contained for an Overleaf upload / local pdfLaTeX build.

Pulls from ../replication-package:
    data/processed/paper_macros.tex      -> ./paper_macros.tex
    data/processed/table{1,2,3}_*.tex    -> ./tables/
    figures/fig_*.pdf                    -> ./figures/

Run AFTER reproduce.py has produced the processed outputs:
    python assemble.py
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
PKG = HERE.parent / "replication-package"
PROC = PKG / "data" / "processed"
FIGS = PKG / "figures"


def main() -> None:
    if not PROC.exists():
        sys.exit(f"Processed data not found at {PROC}. Run reproduce.py first.")

    macros = PROC / "paper_macros.tex"
    if macros.exists():
        shutil.copy2(macros, HERE / "paper_macros.tex")
        print(f"copied {macros.name}")
    else:
        print("WARNING: paper_macros.tex missing — run `python reproduce.py --macros-only`")

    tables_dir = HERE / "tables"
    tables_dir.mkdir(exist_ok=True)
    for tex in sorted(PROC.glob("table*_*.tex")):
        shutil.copy2(tex, tables_dir / tex.name)
        print(f"copied tables/{tex.name}")

    figs_dir = HERE / "figures"
    figs_dir.mkdir(exist_ok=True)
    n = 0
    for pdf in sorted(FIGS.glob("fig_*.pdf")):
        shutil.copy2(pdf, figs_dir / pdf.name)
        n += 1
    print(f"copied {n} figures")

    print("\nManuscript assembled. Build with pdfLaTeX + BibTeX, or upload this "
          "folder into the Elsevier els-cas Overleaf template.")


if __name__ == "__main__":
    main()
