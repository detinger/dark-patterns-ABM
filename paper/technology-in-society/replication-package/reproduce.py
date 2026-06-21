#!/usr/bin/env python3
"""
reproduce.py — regenerate every table and figure in the
"Technology in Society" Dark Patterns ABM paper from the simulation model.

This is the single entry point of the replication package. It runs the seven
scenarios reported in the paper, each replicated over many random seeds, and
emits:

    data/processed/per_run_final.csv      one row per (scenario, seed): final-step metrics
    data/processed/table1_intensity.*     Table I  — intensity comparison (mean +/- 95% CI)
    data/processed/table2_churn_by_type.* Table II — churn by user type
    data/processed/table3_per_pattern.*   Table III — single-pattern impact at intensity 0.50
    data/processed/tipping_points.*       tipping-point trigger fractions and mean steps
    data/processed/sensitivity.csv        local one-at-a-time sensitivity analysis
    data/processed/timeseries/<scen>.csv  per-step mean +/- 95% CI trajectories (for figures)
    data/processed/run_manifest.json      provenance: package versions, seeds, parameters
    data/raw/<scenario>/seed_<NN>.csv.gz  full per-step output of every individual run
    figures/*.pdf                         vector figures used in the manuscript

Determinism
-----------
Each run is fully determined by its (scenario, seed) pair. The model routes all
randomness through a single seeded RNG (Mesa `random.Random(seed)` + derived
numpy Generator), so re-running this script on the same code + dependency
versions reproduces byte-identical output. See REPRODUCTION.md.

Usage
-----
    python reproduce.py                 # full run: 7 scenarios x 100 seeds + sensitivity + figures
    python reproduce.py --quick         # smoke test: 5 seeds, no sensitivity (fast)
    python reproduce.py --replicates 50 # custom replicate count
    python reproduce.py --no-figures    # skip figure rendering
    python reproduce.py --no-sensitivity
    python reproduce.py --no-raw        # do not write the bulky per-run raw CSVs

Run from the replication-package directory using the backend's pinned
environment (see requirements.lock / REPRODUCTION.md).
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import platform as _platform
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

# --------------------------------------------------------------------------
# Paths: make the backend model package importable (single source of truth).
# --------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[2]          # .../dark-matters-ABM
BACKEND_DIR = REPO_ROOT / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from app.simulation.config import (          # noqa: E402
    SCENARIOS,
    DEFAULT_NUM_AGENTS,
    DEFAULT_MAX_STEPS,
    DEFAULT_SOCIAL_INFLUENCE_STRENGTH,
)
from app.simulation.model import DarkPatternTrustModel  # noqa: E402
from app.simulation.run import run_scenario             # noqa: E402

# --------------------------------------------------------------------------
# Experimental design (matches the paper).
# --------------------------------------------------------------------------
NUM_AGENTS = DEFAULT_NUM_AGENTS     # 500
MAX_STEPS = DEFAULT_MAX_STEPS       # 312 (= 6 years, 1 step = 1 week)
DEFAULT_REPLICATES = 100
CI_Z = 1.96                         # 95% normal-approximation half-width (n>=100)

# Seven scenarios reported in the paper, in table order.
INTENSITY_SCENARIOS = ["control", "low_intensity", "medium_intensity", "high_intensity"]
PATTERN_SCENARIOS = ["forced_trial_only", "hard_cancel_only", "drip_pricing_only"]
PAPER_SCENARIOS = INTENSITY_SCENARIOS + PATTERN_SCENARIOS

USER_TYPES = ["skeptic", "naive", "activist"]
TIPPING_POINTS = ["trust_collapse", "social_contagion", "churn_cascade", "extractive_divergence"]

# Final-step scalar metrics captured per run.
FINAL_METRICS = [
    "cumulative_churn", "mean_trust_all", "mean_trust", "mean_harm",
    "platform_reputation", "reputation", "cumulative_revenue", "cumulative_costs",
    "net_value", "opportunity_cost", "cumulative_projected_revenue",
    "tipping_points_triggered_count", "active_users",
    "cumulative_negative_wom_count", "cumulative_positive_wom_count",
    "trust_collapse_step", "social_contagion_step", "churn_cascade_step",
    "extractive_divergence_step",
    "trust_collapse_triggered", "social_contagion_triggered",
    "churn_cascade_triggered", "extractive_divergence_triggered",
    "churned_skeptic", "churned_naive", "churned_activist",
    "trust_skeptic", "trust_naive", "trust_activist",
]

# Metrics aggregated as per-step trajectories (for the figures).
TS_METRICS = [
    "mean_trust_all", "mean_trust", "cumulative_churn", "mean_harm",
    "negative_wom_rate", "step_negative_wom_count", "platform_reputation",
    "step_revenue", "cumulative_revenue", "opportunity_cost",
    "active_users", "trust_skeptic", "trust_naive", "trust_activist",
    "churned_skeptic", "churned_naive", "churned_activist",
]

# Omitting CreationDate/ModDate makes matplotlib PDFs byte-reproducible across
# runs (same matplotlib version), so checksums verify bit-for-bit.
PDF_META = {"CreationDate": None}

OUT = SCRIPT_DIR
DATA_RAW = OUT / "data" / "raw"
DATA_PROC = OUT / "data" / "processed"
TS_DIR = DATA_PROC / "timeseries"
FIG_DIR = OUT / "figures"

# Pretty names for tables/figures.
SCEN_LABEL = {
    "control": "Control",
    "low_intensity": "Low (0.20)",
    "medium_intensity": "Medium (0.40)",
    "high_intensity": "High (0.80)",
    "forced_trial_only": "Forced Trial",
    "hard_cancel_only": "Hard Cancel",
    "drip_pricing_only": "Drip Pricing",
}


# ==========================================================================
# Helpers
# ==========================================================================
def get_versions() -> dict:
    """Capture environment provenance for the run manifest."""
    import importlib

    versions = {
        "python": _platform.python_version(),
        "platform": _platform.platform(),
        "numpy": np.__version__,
        "pandas": pd.__version__,
    }
    for pkg in ("mesa", "networkx"):
        try:
            versions[pkg] = importlib.import_module(pkg).__version__
        except Exception:  # pragma: no cover
            versions[pkg] = "unknown"
    try:
        import subprocess

        commit = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=str(REPO_ROOT),
            capture_output=True, text=True, timeout=10,
        )
        versions["git_commit"] = commit.stdout.strip() or "unknown"
    except Exception:  # pragma: no cover
        versions["git_commit"] = "unknown"
    return versions


def mean_ci(values: np.ndarray) -> tuple[float, float, float, float]:
    """Return (mean, sd, sem, ci95_halfwidth) using a normal approximation."""
    values = np.asarray(values, dtype=float)
    n = len(values)
    if n == 0:
        return (math.nan, math.nan, math.nan, math.nan)
    mean = float(np.mean(values))
    sd = float(np.std(values, ddof=1)) if n > 1 else 0.0
    sem = sd / math.sqrt(n) if n > 0 else 0.0
    return (mean, sd, sem, CI_Z * sem)


def fmt(mean: float, ci: float, decimals: int = 2, pct: bool = False) -> str:
    """Format 'mean +/- ci' for a LaTeX/markdown table cell."""
    scale = 100.0 if pct else 1.0
    suffix = r"\%" if pct else ""
    return f"{mean * scale:.{decimals}f} $\\pm$ {ci * scale:.{decimals}f}{suffix}"


# ==========================================================================
# Simulation drivers
# ==========================================================================
def simulate_custom(kwargs: dict, seed: int):
    """Build + run a model with explicit kwargs (used for sensitivity analysis)."""
    model = DarkPatternTrustModel(
        num_users=NUM_AGENTS, seed=seed, max_steps=MAX_STEPS, **kwargs
    )
    for _ in range(MAX_STEPS):
        model.step()
    return model, model.datacollector.get_model_vars_dataframe()


def per_type_totals(model) -> dict:
    """Count agents and churned agents per user type from the model object."""
    out = {}
    for t in USER_TYPES:
        agents_t = [a for a in model.user_agents if a.user_type == t]
        out[f"n_{t}"] = len(agents_t)
        out[f"churned_{t}_total"] = sum(1 for a in agents_t if not a.active)
    return out


def run_scenario_replicates(scenario: str, seeds: list[int], write_raw: bool):
    """Run one scenario across all seeds; return (final_rows, ts_stack).

    final_rows : list[dict]    final-step metrics + per-type totals, one per seed
    ts_stack   : dict[str -> np.ndarray (n_seeds, MAX_STEPS+1?)]  per-step trajectories
    """
    final_rows = []
    ts_collect = {m: [] for m in TS_METRICS}
    raw_dir = DATA_RAW / scenario
    if write_raw:
        raw_dir.mkdir(parents=True, exist_ok=True)

    for seed in seeds:
        model, df = run_scenario(scenario, NUM_AGENTS, MAX_STEPS, seed)

        row = {"scenario": scenario, "seed": seed}
        last = df.iloc[-1]
        for m in FINAL_METRICS:
            row[m] = float(last[m]) if m in df.columns else math.nan
        row.update(per_type_totals(model))
        final_rows.append(row)

        for m in TS_METRICS:
            if m in df.columns:
                ts_collect[m].append(df[m].to_numpy(dtype=float))

        if write_raw:
            df.to_csv(raw_dir / f"seed_{seed:03d}.csv.gz",
                      compression={"method": "gzip", "mtime": 0})

    # Stack trajectories into (n_seeds, n_steps); trim to common length.
    ts_stack = {}
    for m, arrs in ts_collect.items():
        if not arrs:
            continue
        min_len = min(len(a) for a in arrs)
        ts_stack[m] = np.vstack([a[:min_len] for a in arrs])
    return final_rows, ts_stack


# ==========================================================================
# Aggregation -> tables
# ==========================================================================
def write_timeseries(scenario: str, ts_stack: dict) -> None:
    """Write per-step mean and 95% CI for each plotted metric."""
    TS_DIR.mkdir(parents=True, exist_ok=True)
    if not ts_stack:
        return
    n_steps = next(iter(ts_stack.values())).shape[1]
    out = {"step": np.arange(n_steps)}
    for m, stack in ts_stack.items():
        mean = stack.mean(axis=0)
        sd = stack.std(axis=0, ddof=1) if stack.shape[0] > 1 else np.zeros(n_steps)
        half = CI_Z * sd / math.sqrt(stack.shape[0])
        out[f"{m}_mean"] = mean
        out[f"{m}_lo"] = mean - half
        out[f"{m}_hi"] = mean + half
    pd.DataFrame(out).to_csv(TS_DIR / f"{scenario}.csv", index=False)


def build_table1(per_run: pd.DataFrame) -> pd.DataFrame:
    """Table I — intensity comparison (mean +/- 95% CI across seeds)."""
    rows = [
        ("Cumulative churn", "cumulative_churn", 1, True),
        ("Mean trust (all)", "mean_trust_all", 3, False),
        ("Mean harm (active)", "mean_harm", 3, False),
        ("Platform reputation", "platform_reputation", 1, False),
        ("Cumulative revenue", "cumulative_revenue", 0, False),
        ("Opportunity cost", "opportunity_cost", 0, False),
        ("Tipping points (of 4)", "tipping_points_triggered_count", 2, False),
    ]
    table = {}
    for scen in INTENSITY_SCENARIOS:
        sub = per_run[per_run.scenario == scen]
        col = {}
        for label, metric, dec, pct in rows:
            mean, _sd, _sem, ci = mean_ci(sub[metric].to_numpy())
            col[label] = fmt(mean, ci, dec, pct)
        table[SCEN_LABEL[scen]] = col
    return pd.DataFrame(table).reindex([r[0] for r in rows])


def build_table2(per_run: pd.DataFrame) -> pd.DataFrame:
    """Table II — churn by user type (count and % of type, mean +/- CI).

    User-type assignment is determined by the seed (drawn at agent creation,
    before any scenario parameter takes effect), so the per-type population N is
    identical across scenarios for a shared seed set. We therefore label each
    row with the mean per-type N over all runs.
    """
    labels = {t: f"{t.capitalize()} (N={float(per_run[f'n_{t}'].mean()):.0f})"
              for t in USER_TYPES}
    table = {}
    for scen in INTENSITY_SCENARIOS:
        sub = per_run[per_run.scenario == scen]
        col = {}
        for t in USER_TYPES:
            churned = sub[f"churned_{t}_total"].to_numpy(dtype=float)
            n_t = sub[f"n_{t}"].to_numpy(dtype=float)
            pct = np.divide(churned, n_t, out=np.zeros_like(churned), where=n_t > 0)
            cm, _s, _e, cci = mean_ci(churned)
            pm, _s2, _e2, pci = mean_ci(pct)
            col[labels[t]] = f"{cm:.0f} $\\pm$ {cci:.0f} ({pm*100:.0f} $\\pm$ {pci*100:.0f}\\%)"
        table[SCEN_LABEL[scen]] = col
    return pd.DataFrame(table).reindex([labels[t] for t in USER_TYPES])


def build_table3(per_run: pd.DataFrame) -> pd.DataFrame:
    """Table III — single-pattern impact at intensity 0.50."""
    rows = [
        ("Cumulative churn", "cumulative_churn", 1, True),
        ("Mean trust (all)", "mean_trust_all", 3, False),
        ("Tipping points (of 4)", "tipping_points_triggered_count", 2, False),
    ]
    table = {}
    for scen in PATTERN_SCENARIOS:
        sub = per_run[per_run.scenario == scen]
        col = {}
        for label, metric, dec, pct in rows:
            mean, _sd, _sem, ci = mean_ci(sub[metric].to_numpy())
            col[label] = fmt(mean, ci, dec, pct)
        # Trust-collapse step among runs that triggered it
        steps = sub["trust_collapse_step"].to_numpy(dtype=float)
        triggered = steps[steps >= 0]
        if len(triggered):
            sm, _s, _e, sci = mean_ci(triggered)
            frac = len(triggered) / len(steps) * 100
            col["Trust Collapse step"] = f"{sm:.0f} $\\pm$ {sci:.0f} ({frac:.0f}\\% of runs)"
        else:
            col["Trust Collapse step"] = "--"
        table[SCEN_LABEL[scen]] = col
    order = ["Cumulative churn", "Mean trust (all)", "Trust Collapse step", "Tipping points (of 4)"]
    return pd.DataFrame(table).reindex(order)


def build_tipping_table(per_run: pd.DataFrame) -> pd.DataFrame:
    """Per-scenario tipping-point trigger fraction and mean trigger step."""
    records = []
    for scen in PAPER_SCENARIOS:
        sub = per_run[per_run.scenario == scen]
        rec = {"scenario": scen}
        for tp in TIPPING_POINTS:
            trig = sub[f"{tp}_triggered"].to_numpy(dtype=float)
            steps = sub[f"{tp}_step"].to_numpy(dtype=float)
            valid = steps[steps >= 0]
            rec[f"{tp}_frac"] = float(np.mean(trig))
            rec[f"{tp}_step_mean"] = float(np.mean(valid)) if len(valid) else math.nan
        records.append(rec)
    return pd.DataFrame(records)


SCEN_KEY = {
    "control": "ctrl", "low_intensity": "low", "medium_intensity": "med",
    "high_intensity": "high", "forced_trial_only": "forced",
    "hard_cancel_only": "hardcancel", "drip_pricing_only": "drip",
}


def _money(x: float) -> str:
    return f"{x:,.0f}".replace(",", "{,}")  # LaTeX-safe thousands separator


def build_paper_macros(per_run: pd.DataFrame, tipping: pd.DataFrame) -> str:
    r"""Emit \newcommand definitions for every inline number cited in the prose.

    The manuscript \input's this file and uses the macros (e.g. \medChurn) so no
    result is ever hardcoded in the text — everything traces to the simulation.
    """
    lines = [
        "% AUTO-GENERATED by reproduce.py — do not edit by hand.",
        "% Inline point estimates (means across seeds). Tables carry the 95% CIs.",
        r"\newcommand{\numReplicates}{" + f"{per_run.groupby('scenario').size().max()}" + "}",
        r"\newcommand{\numAgents}{" + f"{NUM_AGENTS}" + "}",
        r"\newcommand{\maxSteps}{" + f"{MAX_STEPS}" + "}",
    ]

    def m(name: str, value: str) -> None:
        lines.append(r"\newcommand{\%s}{%s}" % (name, value))

    tip_by_scen = {r["scenario"]: r for _, r in tipping.iterrows()}

    for scen in PAPER_SCENARIOS:
        key = SCEN_KEY[scen]
        sub = per_run[per_run.scenario == scen]
        churn = sub["cumulative_churn"].mean() * 100
        trust = sub["mean_trust_all"].mean()
        harm = sub["mean_harm"].mean()
        rep = sub["platform_reputation"].mean()
        rev = sub["cumulative_revenue"].mean()
        opp = sub["opportunity_cost"].mean()
        tp = sub["tipping_points_triggered_count"].mean()
        m(f"{key}Churn", f"{churn:.1f}\\%")
        m(f"{key}Trust", f"{trust:.3f}")
        m(f"{key}Harm", f"{harm:.3f}")
        m(f"{key}Rep", f"{rep:.1f}")
        m(f"{key}Rev", _money(rev))
        m(f"{key}Opp", _money(opp))
        m(f"{key}Tp", f"{tp:.0f}")
        # Tipping-point steps (mean over runs that triggered)
        rec = tip_by_scen.get(scen, {})
        for tp_name, short in [("trust_collapse", "Collapse"),
                               ("social_contagion", "Contagion"),
                               ("churn_cascade", "Cascade"),
                               ("extractive_divergence", "Extractive")]:
            step = rec.get(f"{tp_name}_step_mean", math.nan)
            frac = rec.get(f"{tp_name}_frac", 0.0)
            if step == step and frac >= 0.5:  # triggered in a majority of runs
                m(f"{key}{short}Step", f"{step:.0f}")

    # Per-user-type churn % at medium and high intensity
    for scen, kpref in [("medium_intensity", "med"), ("high_intensity", "high")]:
        sub = per_run[per_run.scenario == scen]
        for t in USER_TYPES:
            churned = sub[f"churned_{t}_total"].to_numpy(dtype=float)
            n_t = sub[f"n_{t}"].to_numpy(dtype=float)
            pct = np.divide(churned, n_t, out=np.zeros_like(churned), where=n_t > 0).mean() * 100
            m(f"{kpref}{t.capitalize()}ChurnPct", f"{pct:.0f}\\%")
    # Mean per-type population N (seed-determined, scenario-independent)
    for t in USER_TYPES:
        m(f"n{t.capitalize()}", f"{per_run[f'n_{t}'].mean():.0f}")

    return "\n".join(lines) + "\n"


def df_to_latex(df: pd.DataFrame, caption: str, label: str) -> str:
    """Render a small table as a booktabs LaTeX table (escaping handled by caller)."""
    cols = list(df.columns)
    colspec = "l" + "r" * len(cols)
    lines = [
        r"\begin{table}[!t]",
        r"\centering",
        f"\\caption{{{caption}}}",
        f"\\label{{{label}}}",
        f"\\begin{{tabular}}{{{colspec}}}",
        r"\toprule",
        "Metric & " + " & ".join(cols) + r" \\",
        r"\midrule",
    ]
    for idx, row in df.iterrows():
        lines.append(f"{idx} & " + " & ".join(str(v) for v in row.tolist()) + r" \\")
    lines += [r"\bottomrule", r"\end{tabular}", r"\end{table}", ""]
    return "\n".join(lines)


# ==========================================================================
# Sensitivity analysis (local, one-at-a-time around the medium baseline)
# ==========================================================================
def baseline_kwargs() -> dict:
    s = SCENARIOS["medium_intensity"]
    return dict(
        dark_pattern_intensity=s["dark_pattern_intensity"],
        pattern_forced_trial=s["patterns"]["forced_trial"],
        pattern_hard_cancel=s["patterns"]["hard_cancel"],
        pattern_drip_pricing=s["patterns"]["drip_pricing"],
        adaptive_platform=s["adaptive_platform"],
        customer_support_quality=s["customer_support_quality"],
        social_influence_strength=DEFAULT_SOCIAL_INFLUENCE_STRENGTH,
    )


SENSITIVITY_GRID = {
    "dark_pattern_intensity": [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.8, 1.0],
    "social_influence_strength": [0.0, 0.05, 0.1, 0.18, 0.3, 0.5],
    "customer_support_quality": [0.0, 0.1, 0.2, 0.3, 0.5, 0.8],
}


def run_sensitivity(seeds: list[int]) -> pd.DataFrame:
    """One-at-a-time sweep of key parameters around the medium baseline."""
    records = []
    out_metrics = ["cumulative_churn", "mean_trust_all", "opportunity_cost",
                   "tipping_points_triggered_count"]
    for param, values in SENSITIVITY_GRID.items():
        for val in values:
            kwargs = baseline_kwargs()
            kwargs[param] = val
            agg = {m: [] for m in out_metrics}
            for seed in seeds:
                _model, df = simulate_custom(kwargs, seed)
                last = df.iloc[-1]
                for m in out_metrics:
                    agg[m].append(float(last[m]))
            rec = {"param": param, "value": val, "n_seeds": len(seeds)}
            for m in out_metrics:
                mean, _sd, _sem, ci = mean_ci(np.asarray(agg[m]))
                rec[f"{m}_mean"] = mean
                rec[f"{m}_ci"] = ci
            records.append(rec)
            print(f"    {param}={val}: churn={rec['cumulative_churn_mean']*100:.1f}% "
                  f"trust={rec['mean_trust_all_mean']:.3f}")
    return pd.DataFrame(records)


# ==========================================================================
# Figures (vector PDF)
# ==========================================================================
def _load_ts(scenario: str) -> pd.DataFrame | None:
    path = TS_DIR / f"{scenario}.csv"
    return pd.read_csv(path) if path.exists() else None


def make_figures(per_run: pd.DataFrame, sensitivity: pd.DataFrame | None) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    FIG_DIR.mkdir(parents=True, exist_ok=True)
    palette = {
        "control": "#2c7fb8", "low_intensity": "#41ab5d",
        "medium_intensity": "#fe9929", "high_intensity": "#d7301f",
    }

    def band(ax, ts, metric, color, label):
        ax.plot(ts["step"], ts[f"{metric}_mean"], color=color, linewidth=2, label=label)
        ax.fill_between(ts["step"], ts[f"{metric}_lo"], ts[f"{metric}_hi"],
                        color=color, alpha=0.18, linewidth=0)

    # Fig 1: mean trust (all) by intensity
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for scen in INTENSITY_SCENARIOS:
        ts = _load_ts(scen)
        if ts is not None:
            band(ax, ts, "mean_trust_all", palette[scen], SCEN_LABEL[scen])
    ax.set_xlabel("Step (week)"); ax.set_ylabel("Mean trust (all users)")
    ax.set_title("Trust trajectories by dark-pattern intensity")
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(FIG_DIR / "fig_trust_by_intensity.pdf", metadata=PDF_META); plt.close(fig)

    # Fig 2: cumulative churn by intensity
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for scen in INTENSITY_SCENARIOS:
        ts = _load_ts(scen)
        if ts is not None:
            band(ax, ts, "cumulative_churn", palette[scen], SCEN_LABEL[scen])
    ax.set_xlabel("Step (week)"); ax.set_ylabel("Cumulative churn (fraction)")
    ax.set_title("Cumulative churn by dark-pattern intensity")
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(FIG_DIR / "fig_churn_by_intensity.pdf", metadata=PDF_META); plt.close(fig)

    # Fig 3: negative WOM rate by intensity
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for scen in INTENSITY_SCENARIOS:
        ts = _load_ts(scen)
        if ts is not None:
            band(ax, ts, "negative_wom_rate", palette[scen], SCEN_LABEL[scen])
    ax.set_xlabel("Step (week)"); ax.set_ylabel("Negative WOM rate (active)")
    ax.set_title("Social contagion by dark-pattern intensity")
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(FIG_DIR / "fig_negwom_by_intensity.pdf", metadata=PDF_META); plt.close(fig)

    # Fig 4: platform reputation by intensity
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for scen in INTENSITY_SCENARIOS:
        ts = _load_ts(scen)
        if ts is not None:
            band(ax, ts, "platform_reputation", palette[scen], SCEN_LABEL[scen])
    ax.set_xlabel("Step (week)"); ax.set_ylabel("Platform reputation (0-100)")
    ax.set_title("Platform reputation by dark-pattern intensity")
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(FIG_DIR / "fig_reputation_by_intensity.pdf", metadata=PDF_META); plt.close(fig)

    # Fig 5: economics — cumulative revenue + opportunity cost by intensity
    fig, ax = plt.subplots(figsize=(7, 4.2))
    for scen in INTENSITY_SCENARIOS:
        ts = _load_ts(scen)
        if ts is not None:
            band(ax, ts, "cumulative_revenue", palette[scen], SCEN_LABEL[scen])
    ax.set_xlabel("Step (week)"); ax.set_ylabel("Cumulative revenue")
    ax.set_title("Cumulative revenue by dark-pattern intensity")
    ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(FIG_DIR / "fig_revenue_by_intensity.pdf", metadata=PDF_META); plt.close(fig)

    # Fig 6: churn by user type at medium intensity (grouped bars, final step)
    fig, ax = plt.subplots(figsize=(7, 4.2))
    width = 0.2
    x = np.arange(len(USER_TYPES))
    for i, scen in enumerate(INTENSITY_SCENARIOS):
        sub = per_run[per_run.scenario == scen]
        pcts, errs = [], []
        for t in USER_TYPES:
            churned = sub[f"churned_{t}_total"].to_numpy(dtype=float)
            n_t = sub[f"n_{t}"].to_numpy(dtype=float)
            pct = np.divide(churned, n_t, out=np.zeros_like(churned), where=n_t > 0)
            m, _s, _e, ci = mean_ci(pct)
            pcts.append(m * 100); errs.append(ci * 100)
        ax.bar(x + (i - 1.5) * width, pcts, width, yerr=errs, capsize=3,
               label=SCEN_LABEL[scen], color=palette[scen])
    ax.set_xticks(x); ax.set_xticklabels([t.capitalize() for t in USER_TYPES])
    ax.set_ylabel("Churn (% of type)"); ax.set_title("Churn by user type and intensity")
    ax.legend(); ax.grid(alpha=0.3, axis="y")
    fig.tight_layout(); fig.savefig(FIG_DIR / "fig_churn_by_type.pdf", metadata=PDF_META); plt.close(fig)

    # Fig 7: per-pattern comparison (final churn & trust)
    fig, ax = plt.subplots(figsize=(7, 4.2))
    x = np.arange(len(PATTERN_SCENARIOS))
    churn_m, churn_e, trust_m, trust_e = [], [], [], []
    for scen in PATTERN_SCENARIOS:
        sub = per_run[per_run.scenario == scen]
        m, _s, _e, ci = mean_ci(sub["cumulative_churn"].to_numpy())
        churn_m.append(m * 100); churn_e.append(ci * 100)
        m2, _s2, _e2, ci2 = mean_ci(sub["mean_trust_all"].to_numpy())
        trust_m.append(m2); trust_e.append(ci2)
    ax.bar(x - 0.2, churn_m, 0.4, yerr=churn_e, capsize=3, label="Cumulative churn (%)", color="#d7301f")
    ax2 = ax.twinx()
    ax2.bar(x + 0.2, trust_m, 0.4, yerr=trust_e, capsize=3, label="Mean trust (all)", color="#2c7fb8")
    ax.set_xticks(x); ax.set_xticklabels([SCEN_LABEL[s] for s in PATTERN_SCENARIOS])
    ax.set_ylabel("Cumulative churn (%)"); ax2.set_ylabel("Mean trust (all)")
    ax.set_title("Single-pattern impact at intensity 0.50")
    ax.grid(alpha=0.3, axis="y")
    fig.tight_layout(); fig.savefig(FIG_DIR / "fig_per_pattern.pdf", metadata=PDF_META); plt.close(fig)

    # Fig 8: sensitivity analysis
    if sensitivity is not None and len(sensitivity):
        fig, axes = plt.subplots(1, 3, figsize=(13, 4))
        for ax, param in zip(axes, SENSITIVITY_GRID):
            sub = sensitivity[sensitivity.param == param].sort_values("value")
            ax.errorbar(sub["value"], sub["cumulative_churn_mean"] * 100,
                        yerr=sub["cumulative_churn_ci"] * 100, marker="o",
                        capsize=3, color="#d7301f", label="Churn (%)")
            ax2 = ax.twinx()
            ax2.errorbar(sub["value"], sub["mean_trust_all_mean"],
                         yerr=sub["mean_trust_all_ci"], marker="s",
                         capsize=3, color="#2c7fb8", label="Trust")
            ax.set_xlabel(param.replace("_", " ")); ax.set_ylabel("Cumulative churn (%)")
            ax2.set_ylabel("Mean trust (all)")
            ax.grid(alpha=0.3)
        fig.suptitle("Local sensitivity analysis (around medium baseline)")
        fig.tight_layout(); fig.savefig(FIG_DIR / "fig_sensitivity.pdf", metadata=PDF_META); plt.close(fig)


# ==========================================================================
# Table + macro writing (shared by full run and --macros-only)
# ==========================================================================
def _write_tables_and_macros(per_run: pd.DataFrame) -> None:
    replicates = int(per_run.groupby("scenario").size().max())
    t1 = build_table1(per_run)
    t2 = build_table2(per_run)
    t3 = build_table3(per_run)
    tp = build_tipping_table(per_run)
    t1.to_csv(DATA_PROC / "table1_intensity.csv")
    t2.to_csv(DATA_PROC / "table2_churn_by_type.csv")
    t3.to_csv(DATA_PROC / "table3_per_pattern.csv")
    tp.to_csv(DATA_PROC / "tipping_points.csv", index=False)
    (DATA_PROC / "table1_intensity.tex").write_text(
        df_to_latex(t1, "Simulation outcomes across intensity levels "
                        f"(312 steps, $N={NUM_AGENTS}$, {replicates} seeds, mean $\\pm$ 95\\% CI).",
                    "tab:intensity"), encoding="utf-8")
    (DATA_PROC / "table2_churn_by_type.tex").write_text(
        df_to_latex(t2, f"Churn by user type across scenarios ({replicates} seeds, mean $\\pm$ 95\\% CI).",
                    "tab:churn_by_type"), encoding="utf-8")
    (DATA_PROC / "table3_per_pattern.tex").write_text(
        df_to_latex(t3, f"Individual pattern impact at intensity 0.50 ({replicates} seeds, mean $\\pm$ 95\\% CI).",
                    "tab:per_pattern"), encoding="utf-8")
    (DATA_PROC / "paper_macros.tex").write_text(
        build_paper_macros(per_run, tp), encoding="utf-8")

    print("\nTABLE I (intensity comparison)\n", t1.to_string())
    print("\nTABLE II (churn by user type)\n", t2.to_string())
    print("\nTABLE III (per-pattern at 0.50)\n", t3.to_string())


def build_checksums() -> None:
    """Write SHA-256 of every deterministic artifact (excludes the manifest,
    which carries timestamps). Verify later with `sha256sum -c checksums.sha256`."""
    targets: list[Path] = []
    for pat in ("data/processed/*.csv", "data/processed/*.tex",
                "data/processed/timeseries/*.csv", "figures/*.pdf"):
        targets += sorted(OUT.glob(pat))
    targets += sorted(DATA_RAW.glob("*/*.csv.gz"))
    lines = []
    for f in targets:
        if f.name in ("run_manifest.json", "checksums.sha256"):
            continue
        digest = hashlib.sha256(f.read_bytes()).hexdigest()
        lines.append(f"{digest}  {f.relative_to(OUT).as_posix()}")
    # Force LF newlines so `sha256sum -c checksums.sha256` works on Unix tooling
    # (the default Windows text mode would emit CRLF and corrupt the filenames).
    (OUT / "checksums.sha256").write_text("\n".join(lines) + "\n",
                                          encoding="utf-8", newline="\n")
    print(f"Wrote checksums for {len(lines)} files -> checksums.sha256")


# ==========================================================================
# Main
# ==========================================================================
def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--replicates", type=int, default=DEFAULT_REPLICATES,
                        help=f"Replicate seeds per scenario (default {DEFAULT_REPLICATES}).")
    parser.add_argument("--sensitivity-replicates", type=int, default=30,
                        help="Seeds per sensitivity grid point (default 30).")
    parser.add_argument("--seed-base", type=int, default=0,
                        help="First seed; seeds are seed_base .. seed_base+replicates-1.")
    parser.add_argument("--quick", action="store_true",
                        help="Fast smoke test: 5 replicates, no sensitivity.")
    parser.add_argument("--no-figures", action="store_true")
    parser.add_argument("--no-sensitivity", action="store_true")
    parser.add_argument("--no-raw", action="store_true",
                        help="Do not write bulky per-run raw CSVs.")
    parser.add_argument("--macros-only", action="store_true",
                        help="Regenerate tables + paper_macros.tex from existing "
                             "data/processed/per_run_final.csv (no simulation).")
    args = parser.parse_args()

    # Windows consoles default to cp1252; force UTF-8 so table output never crashes.
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # pragma: no cover
        pass

    if args.macros_only:
        per_run = pd.read_csv(DATA_PROC / "per_run_final.csv")
        _write_tables_and_macros(per_run)
        build_checksums()
        print(f"Regenerated tables + paper_macros.tex in {DATA_PROC}")
        return

    replicates = 5 if args.quick else args.replicates
    do_sensitivity = not (args.quick or args.no_sensitivity)
    seeds = list(range(args.seed_base, args.seed_base + replicates))

    DATA_PROC.mkdir(parents=True, exist_ok=True)
    print(f"Reproduction run: {len(PAPER_SCENARIOS)} scenarios x {replicates} seeds "
          f"(N={NUM_AGENTS}, steps={MAX_STEPS})")
    started = datetime.now(timezone.utc)

    all_final = []
    for scen in PAPER_SCENARIOS:
        print(f"  scenario '{scen}' ...", flush=True)
        final_rows, ts_stack = run_scenario_replicates(scen, seeds, write_raw=not args.no_raw)
        all_final.extend(final_rows)
        write_timeseries(scen, ts_stack)

    per_run = pd.DataFrame(all_final)
    per_run.to_csv(DATA_PROC / "per_run_final.csv", index=False)

    _write_tables_and_macros(per_run)

    # Sensitivity
    sensitivity = None
    if do_sensitivity:
        print("\nSensitivity analysis ...")
        sens_seeds = list(range(args.seed_base, args.seed_base + args.sensitivity_replicates))
        sensitivity = run_sensitivity(sens_seeds)
        sensitivity.to_csv(DATA_PROC / "sensitivity.csv", index=False)

    # Figures
    if not args.no_figures:
        print("\nRendering figures ...")
        make_figures(per_run, sensitivity)

    # Manifest
    finished = datetime.now(timezone.utc)
    manifest = {
        "title": "Dark Patterns ABM — reproduction manifest",
        "started_utc": started.isoformat(),
        "finished_utc": finished.isoformat(),
        "duration_seconds": (finished - started).total_seconds(),
        "num_agents": NUM_AGENTS,
        "max_steps": MAX_STEPS,
        "replicates": replicates,
        "seed_base": args.seed_base,
        "seeds": seeds,
        "ci_z": CI_Z,
        "scenarios": {s: SCENARIOS[s] for s in PAPER_SCENARIOS},
        "sensitivity_grid": SENSITIVITY_GRID if do_sensitivity else None,
        "sensitivity_replicates": args.sensitivity_replicates if do_sensitivity else None,
        "versions": get_versions(),
    }
    (DATA_PROC / "run_manifest.json").write_text(
        json.dumps(manifest, indent=2, default=str), encoding="utf-8")

    build_checksums()

    print(f"\nDone in {manifest['duration_seconds']:.0f}s. Outputs in {DATA_PROC}")


if __name__ == "__main__":
    main()
