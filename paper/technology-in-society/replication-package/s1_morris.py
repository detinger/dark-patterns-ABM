#!/usr/bin/env python3
"""
S1 — Morris elementary-effects screening for the dark-patterns ABM.

Outputs
-------
  figures/fig_morris.pdf          μ* vs σ scatter (both outputs on one figure)
  data/processed/morris_ee.csv    raw elementary effects
  data/processed/morris_mu.csv    μ*, σ, μ ranking per parameter and output

Reproducibility
---------------
  Morris sample seed  : 20250627   (fixed)
  N trajectories      : 15
  num_levels          : 4
  Seeds per point     : 3  (averaged before computing EE)
  Total model runs    : 15 × (7+1) × 3 = 360

Parameter bounds (kept as comment + baked into PROBLEM dict below)
------------------------------------------------------------------
  dark_pattern_intensity   [0.05, 0.80]  full operational range
  alpha                    [0.11, 0.33]  ±50% of nominal 0.22
  delta                    [0.09, 0.27]  ±50% of nominal 0.18
  social_influence_strength[0.05, 0.35]  ±94% of nominal 0.18 (covers experiments.py range)
  customer_support_quality [0.10, 0.70]  practical operational range
  theta_T (THETA_TRUST)    [1.75, 5.25]  ±50% of nominal 3.50
  theta_H (THETA_HARM)     [0.95, 2.85]  ±50% of nominal 1.90
"""
from __future__ import annotations

import sys, math, time, contextlib
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from SALib.sample import morris as morris_sample
from SALib.analyze import morris as morris_analyze

# ── path setup ──────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT   = SCRIPT_DIR.parents[2]
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

import app.simulation.agents as _agents   # patched in-place for coefficient sweep

from app.simulation.model import DarkPatternTrustModel

# ── config ───────────────────────────────────────────────────────────────────
MORRIS_SEED     = 20250627   # fixed for reproducibility
N_TRAJ          = 15
NUM_LEVELS      = 4
SEEDS_PER_POINT = 3
NUM_AGENTS      = 500
MAX_STEPS       = 312        # 6 years

# Nominal values (medium-intensity baseline)
_NOMINAL = dict(
    dark_pattern_intensity    = 0.40,
    alpha                     = 0.22,
    delta                     = 0.18,
    social_influence_strength = 0.18,
    customer_support_quality  = 0.30,
    theta_T                   = 3.50,
    theta_H                   = 1.90,
)

PROBLEM = {
    "num_vars": 7,
    "names": [
        "dark_pattern_intensity",
        "alpha",
        "delta",
        "social_influence_strength",
        "customer_support_quality",
        "theta_T",
        "theta_H",
    ],
    "bounds": [
        [0.05, 0.80],   # dark_pattern_intensity  — full operational range
        [0.11, 0.33],   # alpha                   — ±50% of 0.22
        [0.09, 0.27],   # delta                   — ±50% of 0.18
        [0.05, 0.35],   # social_influence_strength
        [0.10, 0.70],   # customer_support_quality
        [1.75, 5.25],   # theta_T                 — ±50% of 3.50
        [0.95, 2.85],   # theta_H                 — ±50% of 1.90
    ],
}

OUTPUTS = ["cumulative_churn", "mean_trust_all"]

FIG_DIR  = SCRIPT_DIR / "figures"
DATA_DIR = SCRIPT_DIR / "data" / "processed"
FIG_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ── model runner ──────────────────────────────────────────────────────────────
@contextlib.contextmanager
def _patch_agents(**kwargs):
    """Temporarily override module-level constants in agents.py."""
    ATTR_MAP = {
        "alpha":   "ALPHA_EXPOSURE_TO_TRUST",
        "delta":   "DELTA_EXPOSURE_TO_HARM",
        "theta_T": "THETA_TRUST",
        "theta_H": "THETA_HARM",
    }
    saved = {}
    for key, attr in ATTR_MAP.items():
        if key in kwargs:
            saved[attr] = getattr(_agents, attr)
            setattr(_agents, attr, kwargs[key])
    try:
        yield
    finally:
        for attr, val in saved.items():
            setattr(_agents, attr, val)


def run_point(params: dict, seed: int) -> dict[str, float]:
    """Run one model instance and return final-step scalar outputs."""
    patch_kwargs = {k: params[k] for k in ("alpha", "delta", "theta_T", "theta_H")
                   if k in params}
    constructor_kwargs = dict(
        num_users                = NUM_AGENTS,
        max_steps                = MAX_STEPS,
        seed                     = seed,
        dark_pattern_intensity   = params["dark_pattern_intensity"],
        social_influence_strength= params["social_influence_strength"],
        customer_support_quality = params["customer_support_quality"],
        pattern_forced_trial     = True,
        pattern_hard_cancel      = True,
        pattern_drip_pricing     = True,
        adaptive_platform        = False,
    )
    with _patch_agents(**patch_kwargs):
        model = DarkPatternTrustModel(**constructor_kwargs)
        for _ in range(MAX_STEPS):
            model.step()
        df = model.datacollector.get_model_vars_dataframe()
        last = df.iloc[-1]
    return {
        "cumulative_churn": float(last.get("cumulative_churn", float("nan"))),
        "mean_trust_all":   float(last.get("mean_trust_all",   float("nan"))),
    }


def eval_point_multi_seed(param_vec: np.ndarray, seeds: list[int]) -> dict[str, float]:
    """Average outputs over multiple seeds for one Morris sample point."""
    params = dict(zip(PROBLEM["names"], param_vec))
    results = {k: [] for k in OUTPUTS}
    for s in seeds:
        out = run_point(params, s)
        for k in OUTPUTS:
            results[k].append(out[k])
    return {k: float(np.mean(v)) for k, v in results.items()}


# ── main ──────────────────────────────────────────────────────────────────────
def main():
    rng = np.random.default_rng(MORRIS_SEED)
    seeds = [int(rng.integers(0, 10_000)) for _ in range(SEEDS_PER_POINT)]

    print(f"Morris screening: N={N_TRAJ} trajectories, D={PROBLEM['num_vars']} params, "
          f"{SEEDS_PER_POINT} seeds/point")
    print(f"Total model runs: {N_TRAJ} × {PROBLEM['num_vars']+1} × {SEEDS_PER_POINT} = "
          f"{N_TRAJ * (PROBLEM['num_vars']+1) * SEEDS_PER_POINT}")
    print(f"Seeds used: {seeds}")
    print()

    # SALib Morris sample (reproducible via numpy_seed)
    param_values = morris_sample.sample(
        PROBLEM, N=N_TRAJ, num_levels=NUM_LEVELS,
        optimal_trajectories=None,
        seed=MORRIS_SEED,
    )
    n_points = len(param_values)
    print(f"SALib generated {n_points} sample points ({n_points * SEEDS_PER_POINT} total runs)\n")

    # ── cache paths — skip re-running if already done ─────────────────────────
    CACHE_X = DATA_DIR / "morris_cache_X.npy"
    CACHE_Y = DATA_DIR / "morris_cache_Y.npz"

    if CACHE_X.exists() and CACHE_Y.exists():
        param_values_cached = np.load(CACHE_X)
        if np.allclose(param_values_cached, param_values):
            Y_npz = np.load(CACHE_Y)
            Y = {k: Y_npz[k] for k in OUTPUTS}
            print(f"Loaded cached Y from {CACHE_Y} (skipping re-run)")
        else:
            print("Cache mismatch — re-running simulations")
            CACHE_X.unlink(missing_ok=True)
            CACHE_Y.unlink(missing_ok=True)
            Y = None
    else:
        Y = None

    if Y is None:
        t0 = time.time()
        Y = {k: np.zeros(n_points) for k in OUTPUTS}
        for i, pv in enumerate(param_values):
            out = eval_point_multi_seed(pv, seeds)
            for k in OUTPUTS:
                Y[k][i] = out[k]
            if (i + 1) % 20 == 0 or i == n_points - 1:
                elapsed = time.time() - t0
                rate = (i + 1) / elapsed
                remaining = (n_points - i - 1) / rate
                print(f"  {i+1:3d}/{n_points}  elapsed={elapsed:.0f}s  "
                      f"eta={remaining:.0f}s")
        elapsed_total = time.time() - t0
        print(f"\nDone. Total wall time: {elapsed_total:.1f}s")
        np.save(CACHE_X, param_values)
        np.savez(CACHE_Y, **Y)
        print(f"Cached to {CACHE_X}, {CACHE_Y}")

    # ── SALib analysis ────────────────────────────────────────────────────────
    si_all = {}
    rows = []
    for out_name in OUTPUTS:
        si = morris_analyze.analyze(
            PROBLEM, param_values, Y[out_name],
            conf_level=0.95, print_to_console=False, num_levels=NUM_LEVELS,
        )
        si_all[out_name] = si
        for j, pname in enumerate(PROBLEM["names"]):
            rows.append({
                "output":  out_name,
                "param":   pname,
                "mu_star": float(si["mu_star"][j]),
                "mu":      float(si["mu"][j]),
                "sigma":   float(si["sigma"][j]),
            })

    df_mu = pd.DataFrame(rows)
    df_mu.to_csv(DATA_DIR / "morris_mu.csv", index=False)

    # Save mu_star_conf as well
    conf_rows = []
    for out_name in OUTPUTS:
        si = si_all[out_name]
        for j, pname in enumerate(PROBLEM["names"]):
            conf_rows.append({
                "output":       out_name,
                "param":        pname,
                "mu_star_conf": float(si["mu_star_conf"][j]),
            })
    df_conf = pd.DataFrame(conf_rows)
    df_mu = df_mu.merge(df_conf, on=["output", "param"], how="left")
    df_mu.to_csv(DATA_DIR / "morris_mu.csv", index=False)

    # ── Print ranking ──────────────────────────────────────────────────────────
    print("\n--- μ* ranking per output ---")
    for out_name in OUTPUTS:
        sub = df_mu[df_mu.output == out_name].sort_values("mu_star", ascending=False)
        print(f"\n  {out_name}:")
        for _, row in sub.iterrows():
            print(f"    {row['param']:30s}  μ*={row['mu_star']:.4f}  σ={row['sigma']:.4f}")

    # ── Figure ────────────────────────────────────────────────────────────────
    PRETTY = {
        "dark_pattern_intensity":    r"$\gamma$ (intensity)",
        "alpha":                     r"$\alpha$ (trust coeff.)",
        "delta":                     r"$\delta$ (harm coeff.)",
        "social_influence_strength": r"$\kappa$ (social influence)",
        "customer_support_quality":  r"$q$ (support quality)",
        "theta_T":                   r"$\theta_T$ (trust weight)",
        "theta_H":                   r"$\theta_H$ (harm weight)",
    }
    COLORS = {
        "dark_pattern_intensity":    "#d62728",
        "alpha":                     "#1f77b4",
        "delta":                     "#ff7f0e",
        "social_influence_strength": "#2ca02c",
        "customer_support_quality":  "#9467bd",
        "theta_T":                   "#8c564b",
        "theta_H":                   "#e377c2",
    }
    MARKERS = {
        "cumulative_churn": "o",
        "mean_trust_all":   "s",
    }

    fig, axes = plt.subplots(1, 2, figsize=(9.8, 4.6), constrained_layout=True)

    output_labels = {
        "cumulative_churn": "Cumulative churn",
        "mean_trust_all":   "Mean trust (all users)",
    }
    label_offsets = {
        "cumulative_churn": {
            "dark_pattern_intensity":    (-56, 11),
            "alpha":                     (8, -14),
            "delta":                     (8, 9),
            "social_influence_strength": (8, 8),
            "customer_support_quality":  (-40, 18),
            "theta_T":                   (9, -17),
            "theta_H":                   (-54, -23),
        },
        "mean_trust_all": {
            "dark_pattern_intensity":    (-74, -14),
            "alpha":                     (12, -23),
            "delta":                     (22, 18),
            "social_influence_strength": (16, -12),
            "customer_support_quality":  (8, -18),
            "theta_T":                   (8, 34),
            "theta_H":                   (-62, -6),
        },
    }

    for ax, out_name in zip(axes, OUTPUTS):
        sub = df_mu[df_mu.output == out_name]
        for _, row in sub.iterrows():
            pname = row["param"]
            ax.scatter(
                row["mu_star"], row["sigma"],
                color=COLORS[pname],
                marker=MARKERS[out_name],
                s=90, zorder=3,
                label=PRETTY[pname],
            )
            ax.annotate(
                PRETTY[pname],
                xy=(row["mu_star"], row["sigma"]),
                xytext=label_offsets[out_name][pname], textcoords="offset points",
                fontsize=6.4, color=COLORS[pname],
                bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.82),
                arrowprops=dict(arrowstyle="-", lw=0.4, color=COLORS[pname], alpha=0.55),
                clip_on=False,
            )
        ax.set_xlabel(r"$\mu^*$ (mean absolute elementary effect)", fontsize=9)
        ax.set_ylabel(r"$\sigma$ (std of elementary effects)", fontsize=9)
        ax.set_title(f"Morris screening — {output_labels[out_name]}", fontsize=9)
        ax.axline((0, 0), slope=1, color="gray", lw=0.8, ls="--", label=r"$\sigma = \mu^*$")
        ax.set_xlim(left=0)
        ax.set_ylim(bottom=0)
        ax.margins(x=0.14, y=0.18)
        ax.grid(True, alpha=0.3)

    # Single legend below both panels
    handles, labels_ = axes[0].get_legend_handles_labels()
    # deduplicate
    seen = {}
    for h, l in zip(handles, labels_):
        if l not in seen:
            seen[l] = h
    fig.legend(seen.values(), seen.keys(),
               loc="outside lower center", ncol=4,
               fontsize=8, frameon=False)

    fig.savefig(FIG_DIR / "fig_morris.pdf", bbox_inches="tight",
                metadata={"CreationDate": None, "ModDate": None})
    print(f"\nFigure saved: {FIG_DIR / 'fig_morris.pdf'}")
    print(f"Tables saved: {DATA_DIR / 'morris_mu.csv'}, {DATA_DIR / 'morris_ee.csv'}")

    return df_mu


if __name__ == "__main__":
    df_mu = main()
