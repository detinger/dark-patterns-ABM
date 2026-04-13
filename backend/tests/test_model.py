"""Tests for app.simulation.model — DarkPatternTrustModel integration tests."""

import pytest
from app.simulation.config import DARK_PATTERN_DEFAULTS


def _make_model(num_users=50, seed=42, **kwargs):
    from app.simulation.model import DarkPatternTrustModel
    return DarkPatternTrustModel(num_users=num_users, seed=seed, **kwargs)


# ── Agent attribute tests ─────────────────────────────────────────────


def test_agent_has_required_attributes():
    model = _make_model()
    for agent in model.user_agents:
        assert hasattr(agent, "user_type")
        assert hasattr(agent, "trust")
        assert hasattr(agent, "digital_literacy")
        assert hasattr(agent, "manipulation_sensitivity")
        assert hasattr(agent, "social_activity")
        assert hasattr(agent, "complaint_propensity")
        assert hasattr(agent, "switching_cost")
        assert hasattr(agent, "pattern_sensitivity")
        assert hasattr(agent, "harm")
        assert hasattr(agent, "active")
        assert hasattr(agent, "warning_awareness")
        assert hasattr(agent, "positive_sentiment")
        assert hasattr(agent, "network_id")


def test_agent_user_types_valid():
    model = _make_model()
    for agent in model.user_agents:
        assert agent.user_type in {"skeptic", "naive", "activist"}


def test_agent_trust_in_range():
    model = _make_model()
    for agent in model.user_agents:
        assert 0.0 <= agent.trust <= 1.0


def test_agent_pattern_sensitivity_has_all_patterns():
    model = _make_model()
    expected_keys = set(DARK_PATTERN_DEFAULTS.keys())
    for agent in model.user_agents:
        assert set(agent.pattern_sensitivity.keys()) == expected_keys


def test_agents_start_active():
    model = _make_model()
    for agent in model.user_agents:
        assert agent.active is True


def test_type_distribution_approximately_correct():
    model = _make_model(num_users=500, seed=99)
    counts = {"skeptic": 0, "naive": 0, "activist": 0}
    for agent in model.user_agents:
        counts[agent.user_type] += 1
    assert 100 < counts["skeptic"] < 200
    assert 200 < counts["naive"] < 300
    assert 50 < counts["activist"] < 150


def test_model_reproducible_with_seed():
    m1 = _make_model(seed=123)
    m2 = _make_model(seed=123)
    for a1, a2 in zip(m1.user_agents, m2.user_agents):
        assert a1.user_type == a2.user_type
        assert a1.trust == a2.trust
        assert a1.digital_literacy == a2.digital_literacy


# ── Simulation dynamics tests ─────────────────────────────────────────


def test_trust_never_exceeds_one():
    model = _make_model()
    for _ in range(10):
        model.step()
    for agent in model.user_agents:
        assert agent.trust <= 1.0


def test_trust_never_below_zero():
    model = _make_model(
        dark_pattern_intensity=0.8,
        pattern_forced_trial=True,
        pattern_hard_cancel=True,
        pattern_drip_pricing=True,
    )
    for _ in range(50):
        model.step()
    for agent in model.user_agents:
        assert agent.trust >= 0.0


def test_churn_is_irreversible():
    model = _make_model(
        dark_pattern_intensity=0.8,
        pattern_forced_trial=True,
        pattern_hard_cancel=True,
        pattern_drip_pricing=True,
    )
    churned_ids = set()
    for _ in range(30):
        model.step()
        for agent in model.user_agents:
            if not agent.active:
                churned_ids.add(agent.unique_id)
    # Verify all previously churned agents are still churned
    for agent in model.user_agents:
        if agent.unique_id in churned_ids:
            assert agent.active is False, f"Agent {agent.unique_id} resurrected"


def test_agents_on_network():
    model = _make_model()
    for agent in model.user_agents:
        assert agent.network_id is not None


def test_control_scenario_stable_trust():
    model = _make_model(
        dark_pattern_intensity=0.0,
        pattern_forced_trial=False,
        pattern_hard_cancel=False,
        pattern_drip_pricing=False,
    )
    initial_trust = sum(a.trust for a in model.user_agents) / len(model.user_agents)
    for _ in range(50):
        model.step()
    active = [a for a in model.user_agents if a.active]
    if active:
        final_trust = sum(a.trust for a in active) / len(active)
        assert abs(initial_trust - final_trust) < 0.05


# ── DataCollector tests ───────────────────────────────────────────────


def test_datacollector_produces_dataframe():
    model = _make_model()
    for _ in range(5):
        model.step()
    df = model.datacollector.get_model_vars_dataframe()
    assert not df.empty
    assert "mean_trust" in df.columns
    assert "active_users" in df.columns
    assert "step_churns" in df.columns
    assert "net_value" in df.columns


def test_datacollector_by_type_metrics():
    model = _make_model()
    model.step()
    df = model.datacollector.get_model_vars_dataframe()
    for utype in ["skeptic", "naive", "activist"]:
        assert f"trust_{utype}" in df.columns
        assert f"churned_{utype}" in df.columns
        assert f"neg_wom_sent_{utype}" in df.columns
        assert f"pos_wom_sent_{utype}" in df.columns


def test_datacollector_per_pattern_metrics():
    model = _make_model()
    model.step()
    df = model.datacollector.get_model_vars_dataframe()
    for pname in DARK_PATTERN_DEFAULTS:
        assert f"detections_{pname}" in df.columns
        assert f"trust_loss_{pname}" in df.columns
        assert f"exposures_{pname}" in df.columns


# ── Comparative scenario tests ────────────────────────────────────────


def test_high_intensity_causes_more_churn():
    control = _make_model(
        dark_pattern_intensity=0.0,
        pattern_forced_trial=False,
        pattern_hard_cancel=False,
        pattern_drip_pricing=False,
        seed=42,
    )
    aggressive = _make_model(
        dark_pattern_intensity=0.8,
        pattern_forced_trial=True,
        pattern_hard_cancel=True,
        pattern_drip_pricing=True,
        seed=42,
    )
    for _ in range(30):
        control.step()
        aggressive.step()
    control_churn = sum(1 for a in control.user_agents if not a.active)
    aggressive_churn = sum(1 for a in aggressive.user_agents if not a.active)
    assert aggressive_churn > control_churn


def test_high_intensity_more_negative_wom():
    control = _make_model(
        dark_pattern_intensity=0.0,
        pattern_forced_trial=False,
        pattern_hard_cancel=False,
        pattern_drip_pricing=False,
        seed=42,
    )
    aggressive = _make_model(
        dark_pattern_intensity=0.8,
        pattern_forced_trial=True,
        pattern_hard_cancel=True,
        pattern_drip_pricing=True,
        seed=42,
    )
    for _ in range(30):
        control.step()
        aggressive.step()
    assert aggressive._cumulative_negative_wom > control._cumulative_negative_wom


def test_adaptive_less_churn_than_static():
    static = _make_model(
        dark_pattern_intensity=0.6,
        pattern_forced_trial=True,
        pattern_hard_cancel=True,
        pattern_drip_pricing=True,
        adaptive_platform=False,
        seed=42,
    )
    adaptive = _make_model(
        dark_pattern_intensity=0.6,
        pattern_forced_trial=True,
        pattern_hard_cancel=True,
        pattern_drip_pricing=True,
        adaptive_platform=True,
        seed=42,
    )
    for _ in range(50):
        static.step()
        adaptive.step()
    static_churn = sum(1 for a in static.user_agents if not a.active)
    adaptive_churn = sum(1 for a in adaptive.user_agents if not a.active)
    # Adaptive platform should cause the same or fewer churns
    assert adaptive_churn <= static_churn


def test_control_generates_positive_wom():
    model = _make_model(
        dark_pattern_intensity=0.0,
        pattern_forced_trial=False,
        pattern_hard_cancel=False,
        pattern_drip_pricing=False,
        seed=42,
    )
    for _ in range(30):
        model.step()
    assert model._cumulative_positive_wom > 0


def test_clean_competitor_reputation_stable():
    model = _make_model(
        dark_pattern_intensity=0.0,
        pattern_forced_trial=False,
        pattern_hard_cancel=False,
        pattern_drip_pricing=False,
        customer_support_quality=0.7,
        seed=42,
    )
    initial_rep = model.platform_reputation
    for _ in range(30):
        model.step()
    # Reputation should not drop significantly (allow small fluctuation)
    assert model.platform_reputation >= initial_rep - 5.0
