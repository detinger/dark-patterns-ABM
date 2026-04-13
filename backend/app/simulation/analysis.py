"""
Post-simulation analysis utilities for the Dark-Matters ABM.

Functions operate on DataFrames produced by Mesa's ``DataCollector``
(one row per simulation step).  They are agnostic to the model itself
and can be used in batch experiments, notebooks, and the web API.

Public API
----------
- ``detect_tipping_point``   – multi-rule tipping-point detection
- ``compute_summary_statistics`` – final-step snapshot
- ``compare_scenarios``      – tabular comparison across scenarios
- ``compare_platforms``      – dark-vs-clean crossover analysis
"""

from __future__ import annotations

import pandas as pd

from app.simulation.config import (
    TRUST_COLLAPSE_THRESHOLD,
    CHURN_ACCELERATION_THRESHOLD,
    WOM_BURST_THRESHOLD,
    TIPPING_POINT_PERSISTENCE,
)


# ---------------------------------------------------------------------------
# Tipping-point detection
# ---------------------------------------------------------------------------

def detect_tipping_point(model_data: pd.DataFrame) -> dict:
    """Detect tipping points in simulation output using three independent rules.

    Each rule requires ``TIPPING_POINT_PERSISTENCE`` (default 3) consecutive
    steps of threshold violation before it fires.

    Rules
    -----
    1. **Trust Collapse** – mean trust drops by more than
       ``TRUST_COLLAPSE_THRESHOLD`` per step for *persistence* consecutive
       steps.
    2. **Churn Acceleration** – step churns / active users exceeds
       ``CHURN_ACCELERATION_THRESHOLD`` for *persistence* consecutive steps.
    3. **WOM Burst** – step negative WOM count exceeds
       ``WOM_BURST_THRESHOLD * active_users`` for *persistence* consecutive
       steps.

    Parameters
    ----------
    model_data : pd.DataFrame
        DataFrame from Mesa's DataCollector with one row per step.

    Returns
    -------
    dict
        ``tipping_point_step``  – earliest step across all triggered rules
        (``None`` if no rule fires).
        ``trigger_rule``        – name of the rule that fired first.
        ``all_triggers``        – list of ``{"rule": str, "step": int}`` for
        every rule that fired.
        ``diagnostics``         – metric values at the tipping-point step.
    """
    n = len(model_data)
    all_triggers: list[dict] = []

    trust = model_data["mean_trust"].values
    churns = model_data["step_churns"].values
    active = model_data["active_users"].values
    neg_wom = model_data["step_negative_wom_count"].values

    # -- Rule 1: Trust Collapse ------------------------------------------------
    consecutive = 0
    for i in range(1, n):
        drop = trust[i - 1] - trust[i]
        if drop > TRUST_COLLAPSE_THRESHOLD:
            consecutive += 1
            if consecutive >= TIPPING_POINT_PERSISTENCE:
                step = i - TIPPING_POINT_PERSISTENCE + 1
                all_triggers.append({"rule": "trust_collapse", "step": int(step)})
                break
        else:
            consecutive = 0

    # -- Rule 2: Churn Acceleration -------------------------------------------
    consecutive = 0
    for i in range(n):
        if active[i] > 0 and (churns[i] / active[i]) > CHURN_ACCELERATION_THRESHOLD:
            consecutive += 1
            if consecutive >= TIPPING_POINT_PERSISTENCE:
                step = i - TIPPING_POINT_PERSISTENCE + 1
                all_triggers.append({"rule": "churn_acceleration", "step": int(step)})
                break
        else:
            consecutive = 0

    # -- Rule 3: WOM Burst ----------------------------------------------------
    consecutive = 0
    for i in range(n):
        if active[i] > 0 and neg_wom[i] > WOM_BURST_THRESHOLD * active[i]:
            consecutive += 1
            if consecutive >= TIPPING_POINT_PERSISTENCE:
                step = i - TIPPING_POINT_PERSISTENCE + 1
                all_triggers.append({"rule": "wom_burst", "step": int(step)})
                break
        else:
            consecutive = 0

    # -- Aggregate results -----------------------------------------------------
    if all_triggers:
        earliest = min(all_triggers, key=lambda t: t["step"])
        tp_step = earliest["step"]
        trigger_rule = earliest["rule"]

        # Clamp index to valid range for diagnostics lookup
        idx = min(tp_step, n - 1)
        diagnostics = {
            "trust_at_tipping": float(trust[idx]),
            "churn_rate_at_tipping": (
                float(churns[idx] / active[idx]) if active[idx] > 0 else 0.0
            ),
            "wom_rate_at_tipping": (
                float(neg_wom[idx] / active[idx]) if active[idx] > 0 else 0.0
            ),
            "active_users_at_tipping": int(active[idx]),
        }
    else:
        tp_step = None
        trigger_rule = None
        diagnostics = {
            "trust_at_tipping": None,
            "churn_rate_at_tipping": None,
            "wom_rate_at_tipping": None,
            "active_users_at_tipping": None,
        }

    return {
        "tipping_point_step": tp_step,
        "trigger_rule": trigger_rule,
        "all_triggers": all_triggers,
        "diagnostics": diagnostics,
    }


# ---------------------------------------------------------------------------
# Summary statistics
# ---------------------------------------------------------------------------

def compute_summary_statistics(model_data: pd.DataFrame) -> dict:
    """Return a final-step snapshot of key simulation metrics.

    Parameters
    ----------
    model_data : pd.DataFrame
        DataFrame from Mesa's DataCollector with one row per step.

    Returns
    -------
    dict
        A flat dictionary of scalar summary values.
    """
    if model_data.empty:
        return {
            "final_avg_trust_active": None,
            "final_avg_trust_all": None,
            "total_churn": None,
            "final_churn_rate": None,
            "total_negative_wom": None,
            "total_positive_wom": None,
            "final_reputation": None,
            "final_net_value": None,
            "final_cumulative_revenue": None,
            "final_cumulative_costs": None,
            "final_active_users": None,
            "steps_run": 0,
        }

    last = model_data.iloc[-1]
    active = last["active_users"]

    return {
        "final_avg_trust_active": float(last["mean_trust"]),
        "final_avg_trust_all": float(last["mean_trust_all"]),
        "total_churn": int(last["cumulative_churn"]),
        "final_churn_rate": (
            float(last["step_churns"] / active) if active > 0 else 0.0
        ),
        "total_negative_wom": int(last["cumulative_negative_wom_count"]),
        "total_positive_wom": int(last["cumulative_positive_wom_count"]),
        "final_reputation": float(last["platform_reputation"]),
        "final_net_value": float(last["net_value"]),
        "final_cumulative_revenue": float(last["cumulative_revenue"]),
        "final_cumulative_costs": float(last["cumulative_costs"]),
        "final_active_users": int(active),
        "steps_run": len(model_data),
    }


# ---------------------------------------------------------------------------
# Scenario comparison
# ---------------------------------------------------------------------------

def compare_scenarios(results: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """Compare summary statistics across multiple scenarios.

    Parameters
    ----------
    results : dict[str, pd.DataFrame]
        Mapping of scenario name to its DataCollector DataFrame.

    Returns
    -------
    pd.DataFrame
        One row per scenario.  If a ``"control"`` scenario is present, delta
        columns (``delta_<metric>``) are appended showing the difference from
        the control for every numeric metric.
    """
    rows: dict[str, dict] = {}
    for name, df in results.items():
        rows[name] = compute_summary_statistics(df)

    comparison = pd.DataFrame.from_dict(rows, orient="index")
    comparison.index.name = "scenario"

    # Add deltas from control if present
    if "control" in comparison.index:
        control_row = comparison.loc["control"]
        for col in comparison.columns:
            if pd.api.types.is_numeric_dtype(comparison[col]):
                comparison[f"delta_{col}"] = comparison[col] - control_row[col]

    return comparison


# ---------------------------------------------------------------------------
# Platform comparison (dark vs. clean)
# ---------------------------------------------------------------------------

def compare_platforms(
    dark_data: pd.DataFrame,
    clean_data: pd.DataFrame,
) -> dict:
    """Compare a dark-pattern platform against a clean competitor.

    Parameters
    ----------
    dark_data : pd.DataFrame
        DataCollector output for the dark-pattern platform.
    clean_data : pd.DataFrame
        DataCollector output for the clean competitor.

    Returns
    -------
    dict
        ``crossover_step`` – first step where clean net_value >= dark
        net_value (``None`` if it never happens).
        ``dark_summary``  – summary statistics for the dark platform.
        ``clean_summary`` – summary statistics for the clean competitor.
    """
    dark_summary = compute_summary_statistics(dark_data)
    clean_summary = compute_summary_statistics(clean_data)

    # Determine crossover step
    crossover_step: int | None = None
    min_len = min(len(dark_data), len(clean_data))
    if min_len > 0:
        dark_nv = dark_data["net_value"].values[:min_len]
        clean_nv = clean_data["net_value"].values[:min_len]
        for i in range(min_len):
            if clean_nv[i] >= dark_nv[i]:
                crossover_step = int(i)
                break

    return {
        "crossover_step": crossover_step,
        "dark_summary": dark_summary,
        "clean_summary": clean_summary,
    }
