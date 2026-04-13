"""Tests for app.simulation.analysis — tipping points and summary stats."""

import pandas as pd
import numpy as np


def _make_stable_data(n_steps=50):
    """Create synthetic model data with stable trust (no tipping point)."""
    return pd.DataFrame({
        "mean_trust": [0.80] * n_steps,
        "active_users": [500] * n_steps,
        "step_churns": [0] * n_steps,
        "step_negative_wom_count": [1] * n_steps,
        "mean_trust_all": [0.80] * n_steps,
        "cumulative_churn": [0.0] * n_steps,
        "cumulative_negative_wom_count": list(range(n_steps)),
        "cumulative_positive_wom_count": list(range(0, n_steps * 2, 2)),
        "platform_reputation": [75.0] * n_steps,
        "net_value": list(range(n_steps)),
        "cumulative_revenue": list(range(0, n_steps * 10, 10)),
        "cumulative_costs": list(range(0, n_steps * 3, 3)),
        "step_churns": [0] * n_steps,
    })


def _make_collapse_data(n_steps=20):
    """Create synthetic data with a trust collapse starting at step 5."""
    trust = [0.80] * 5 + [0.80 - 0.05 * i for i in range(1, n_steps - 4)]
    trust = [max(0.0, t) for t in trust]
    return pd.DataFrame({
        "mean_trust": trust[:n_steps],
        "active_users": [500] * n_steps,
        "step_churns": [0] * 5 + [20] * (n_steps - 5),
        "step_negative_wom_count": [2] * 5 + [300] * (n_steps - 5),
        "mean_trust_all": trust[:n_steps],
        "cumulative_churn": [0.0] * 5 + [0.04 * i for i in range(1, n_steps - 4)],
        "cumulative_negative_wom_count": list(range(n_steps)),
        "cumulative_positive_wom_count": [0] * n_steps,
        "platform_reputation": [70.0] * n_steps,
        "net_value": list(range(n_steps)),
        "cumulative_revenue": list(range(0, n_steps * 10, 10)),
        "cumulative_costs": list(range(0, n_steps * 5, 5)),
    })


def test_detect_tipping_point_finds_collapse():
    from app.simulation.analysis import detect_tipping_point
    data = _make_collapse_data(n_steps=20)
    result = detect_tipping_point(data)
    assert result["tipping_point_step"] is not None
    assert result["trigger_rule"] is not None
    assert len(result["all_triggers"]) > 0


def test_detect_tipping_point_stable_returns_none():
    from app.simulation.analysis import detect_tipping_point
    data = _make_stable_data(n_steps=50)
    result = detect_tipping_point(data)
    assert result["tipping_point_step"] is None
    assert result["trigger_rule"] is None


def test_detect_tipping_point_diagnostics():
    from app.simulation.analysis import detect_tipping_point
    data = _make_collapse_data(n_steps=20)
    result = detect_tipping_point(data)
    diag = result["diagnostics"]
    assert "trust_at_tipping" in diag
    assert "churn_rate_at_tipping" in diag
    assert "wom_rate_at_tipping" in diag
    assert "active_users_at_tipping" in diag
    # Since a tipping point was found, values should be populated
    if result["tipping_point_step"] is not None:
        assert diag["trust_at_tipping"] is not None
        assert diag["active_users_at_tipping"] is not None


def test_compute_summary_statistics_keys():
    from app.simulation.analysis import compute_summary_statistics
    data = _make_stable_data(n_steps=50)
    stats = compute_summary_statistics(data)
    expected_keys = {
        "final_avg_trust_active", "final_avg_trust_all",
        "total_churn", "final_churn_rate",
        "total_negative_wom", "total_positive_wom",
        "final_reputation", "final_net_value",
        "final_cumulative_revenue", "final_cumulative_costs",
        "final_active_users", "steps_run",
    }
    assert expected_keys.issubset(set(stats.keys()))


def test_compare_scenarios_returns_dataframe():
    from app.simulation.analysis import compare_scenarios
    results = {
        "control": _make_stable_data(n_steps=20),
        "aggressive": _make_collapse_data(n_steps=20),
    }
    df = compare_scenarios(results)
    assert isinstance(df, pd.DataFrame)
    assert "control" in df.index
    assert "aggressive" in df.index
