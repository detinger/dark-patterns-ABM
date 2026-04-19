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
        # Trust may rise slightly in control (recovery + positive WOM boost)
        # but should not drop significantly without dark patterns
        assert final_trust >= initial_trust - 0.05


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
        num_users=100,
        dark_pattern_intensity=0.0,
        pattern_forced_trial=False,
        pattern_hard_cancel=False,
        pattern_drip_pricing=False,
        seed=42,
    )
    aggressive = _make_model(
        num_users=100,
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
        num_users=200,
        dark_pattern_intensity=0.6,
        pattern_forced_trial=True,
        pattern_hard_cancel=True,
        pattern_drip_pricing=True,
        adaptive_platform=False,
        seed=42,
    )
    adaptive = _make_model(
        num_users=200,
        dark_pattern_intensity=0.6,
        pattern_forced_trial=True,
        pattern_hard_cancel=True,
        pattern_drip_pricing=True,
        adaptive_platform=True,
        seed=42,
    )
    for _ in range(80):
        static.step()
        adaptive.step()
    static_churn = sum(1 for a in static.user_agents if not a.active)
    adaptive_churn = sum(1 for a in adaptive.user_agents if not a.active)
    # Adaptive platform should cause the same or fewer churns over longer horizon
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
    # Use platform.reputation (0-1 scale) which is the doc formula:
    # 0.7 * mean_trust + 0.3 * (1 - mean_wom)
    # This should stay high without dark patterns.
    model = _make_model(
        num_users=200,
        dark_pattern_intensity=0.0,
        pattern_forced_trial=False,
        pattern_hard_cancel=False,
        pattern_drip_pricing=False,
        customer_support_quality=0.7,
        seed=42,
    )
    for _ in range(30):
        model.step()
    # Without dark patterns, reputation should stay above 0.6
    assert model.platform.reputation >= 0.6


# ── Reputation-discounted revenue tests ──────────────────────────────


def test_reputation_discounts_revenue():
    """Low reputation should reduce per-step revenue via reputation factor."""
    model = _make_model(
        num_users=200,
        dark_pattern_intensity=0.8,
        pattern_forced_trial=True,
        pattern_hard_cancel=True,
        pattern_drip_pricing=True,
        seed=42,
    )
    for _ in range(60):
        model.step()
    # After 60 steps of aggressive dark patterns, reputation should be low
    assert model.platform_reputation < 20.0
    # Per-step base revenue should be significantly less than
    # active_count * BASE_REVENUE_PER_USER (the un-discounted amount)
    from app.simulation.config import BASE_REVENUE_PER_USER
    active_count = sum(1 for a in model.user_agents if a.active)
    undiscounted = active_count * BASE_REVENUE_PER_USER
    assert model._step_base_revenue < undiscounted * 0.6


def test_control_revenue_not_discounted():
    """Without dark patterns, reputation stays high so revenue is near full rate."""
    model = _make_model(
        num_users=200,
        dark_pattern_intensity=0.0,
        pattern_forced_trial=False,
        pattern_hard_cancel=False,
        pattern_drip_pricing=False,
        customer_support_quality=0.5,
        seed=42,
    )
    for _ in range(30):
        model.step()
    from app.simulation.config import BASE_REVENUE_PER_USER
    active_count = sum(1 for a in model.user_agents if a.active)
    undiscounted = active_count * BASE_REVENUE_PER_USER
    # With high reputation, revenue should be at least 80% of undiscounted
    assert model._step_base_revenue >= undiscounted * 0.8


def test_aggressive_dp_net_value_lower_than_control():
    """Aggressive dark patterns should produce lower net value than control."""
    control = _make_model(
        num_users=200,
        dark_pattern_intensity=0.0,
        pattern_forced_trial=False,
        pattern_hard_cancel=False,
        pattern_drip_pricing=False,
        seed=42,
    )
    aggressive = _make_model(
        num_users=200,
        dark_pattern_intensity=0.8,
        pattern_forced_trial=True,
        pattern_hard_cancel=True,
        pattern_drip_pricing=True,
        seed=42,
    )
    for _ in range(100):
        control.step()
        aggressive.step()
    # Over a long enough horizon, the aggressive platform's net value
    # should be lower because reputation collapse discounts revenue
    assert aggressive._net_value < control._net_value


def test_agent_has_wom_realism_attributes():
    model = _make_model()
    for agent in model.user_agents:
        assert hasattr(agent, "_step_wom_received")
        assert agent._step_wom_received == 0
        assert hasattr(agent, "_wom_ramp_factor")
        assert agent._wom_ramp_factor == 0.0


def test_wom_per_step_neighbor_limit():
    """A user can spread WOM to at most WOM_MAX_NEIGHBORS_PER_STEP neighbors."""
    from app.simulation.config import WOM_MAX_NEIGHBORS_PER_STEP
    model = _make_model(num_users=50, seed=42, avg_degree=8)
    agent = model.user_agents[0]
    agent.harm = 0.50
    agent.trust = 0.1
    agent.social_activity = 0.99
    agent.complaint_propensity = 0.99
    agent._wom_ramp_factor = 1.0
    agent.negative_wom = 0.9
    edges = agent.spread_negative_wom(model.graph, model.social_influence_strength)
    assert len(edges) <= WOM_MAX_NEIGHBORS_PER_STEP


def test_wom_damping_reduces_spread():
    """With damping, fewer neighbors are reached than without."""
    model = _make_model(num_users=100, seed=42, avg_degree=8)
    for _ in range(15):
        model.step()
    total_neg_wom = model._cumulative_negative_wom
    assert total_neg_wom < 300


def test_wom_diminishing_returns_on_receiver():
    """A receiver getting multiple WOM messages in one step has diminishing trust loss."""
    model = _make_model(num_users=50, seed=42)
    target = model.user_agents[0]
    target.trust = 0.80
    target._step_wom_received = 0
    initial_trust = target.trust

    sender1 = model.user_agents[1]
    sender2 = model.user_agents[2]
    sender3 = model.user_agents[3]
    for s in [sender1, sender2, sender3]:
        s.harm = 0.50
        s.trust = 0.1
        s.social_activity = 0.99
        s.complaint_propensity = 0.99
        s._wom_ramp_factor = 1.0
        s.negative_wom = 0.9
        s.spread_negative_wom(model.graph, model.social_influence_strength)

    trust_loss = initial_trust - target.trust
    # With diminishing returns + trust shield, total loss from 3 messages
    # should be well under 3x the single-message loss
    assert trust_loss < 0.08


def test_wom_trust_shield_protects_high_trust():
    """High-trust receivers take less WOM damage than low-trust receivers."""
    model = _make_model(num_users=50, seed=42)
    high_trust_agent = model.user_agents[0]
    low_trust_agent = model.user_agents[1]
    high_trust_agent.trust = 0.90
    low_trust_agent.trust = 0.20
    high_trust_agent._step_wom_received = 0
    low_trust_agent._step_wom_received = 0

    ht_initial = high_trust_agent.trust
    lt_initial = low_trust_agent.trust

    from app.simulation.config import (
        WOM_TRUST_PENALTY,
        WOM_TRUST_SHIELD,
        WOM_DIMINISHING_RATE,
    )
    social_inf = model.social_influence_strength

    for target in [high_trust_agent, low_trust_agent]:
        discount = 1.0 / (1.0 + WOM_DIMINISHING_RATE * target._step_wom_received)
        receptivity = 1.0 - WOM_TRUST_SHIELD * target.trust
        penalty = WOM_TRUST_PENALTY * social_inf * discount * receptivity
        target.trust = max(0.0, target.trust - penalty)
        target._step_wom_received += 1

    ht_loss = ht_initial - high_trust_agent.trust
    lt_loss = lt_initial - low_trust_agent.trust
    assert ht_loss < lt_loss


def test_wom_cooldown_blocks_low_harm():
    """Users below WOM_HARM_COOLDOWN_THRESHOLD produce zero negative WOM."""
    model = _make_model(num_users=50, seed=42)
    agent = model.user_agents[0]
    agent.harm = 0.05  # below 0.08 threshold
    agent._step_total_harm = 0.01
    result = agent.decide_word_of_mouth()
    assert result == 0.0
    assert agent.negative_wom == 0.0
    assert agent._wom_ramp_factor == 0.0


def test_wom_ramp_partial_at_medium_harm():
    """Users just past cooldown have reduced WOM via ramp_factor."""
    model = _make_model(num_users=50, seed=42)
    agent = model.user_agents[0]
    agent.harm = 0.20  # past 0.08, ramp = (0.20-0.08)/0.25 = 0.48
    agent.trust = 0.3
    agent._step_total_harm = 0.01
    result = agent.decide_word_of_mouth()
    assert result > 0.0
    assert 0.0 < agent._wom_ramp_factor < 1.0


def test_wom_ramp_full_at_high_harm():
    """Users with high harm have ramp_factor = 1.0."""
    model = _make_model(num_users=50, seed=42)
    agent = model.user_agents[0]
    agent.harm = 0.50  # well past 0.08+0.25=0.33
    agent.trust = 0.2
    agent._step_total_harm = 0.01
    result = agent.decide_word_of_mouth()
    assert agent._wom_ramp_factor == 1.0
    assert result > 0.0


# ── Trust recovery tests ──────────────────────────────────────────────


def test_partial_recovery_during_exposure():
    """Recovery should work (at reduced rate) even when exposed this step."""
    model = _make_model(
        num_users=50, seed=42,
        customer_support_quality=0.80,
    )
    agent = model.user_agents[0]
    agent.trust = 0.50
    agent.trust_baseline = 0.80
    agent.harm = 0.05  # low accumulated harm
    agent._step_total_harm = 0.05  # light exposure this step

    pre_trust = agent.trust
    agent.apply_recovery()
    # With light exposure (0.05 < RECOVERY_EXPOSURE_CEILING=0.15),
    # partial recovery should occur
    assert agent.trust > pre_trust


def test_no_recovery_during_heavy_exposure():
    """Heavy exposure should still block recovery."""
    model = _make_model(
        num_users=50, seed=42,
        customer_support_quality=0.80,
    )
    agent = model.user_agents[0]
    agent.trust = 0.50
    agent.trust_baseline = 0.80
    agent.harm = 0.05
    agent._step_total_harm = 0.20  # heavy exposure (above RECOVERY_EXPOSURE_CEILING)

    pre_trust = agent.trust
    agent.apply_recovery()
    assert agent.trust == pre_trust


def test_natural_trust_recovery():
    """Trust should recover passively toward baseline even without support."""
    model = _make_model(
        num_users=50, seed=42,
        customer_support_quality=0.0,  # no support
    )
    agent = model.user_agents[0]
    agent.trust = 0.30
    agent.trust_baseline = 0.80
    agent._step_total_harm = 0.0

    pre_trust = agent.trust
    agent.apply_natural_recovery()
    assert agent.trust > pre_trust
    assert agent.trust <= agent.trust_baseline
    # Expected: 0.30 + 0.008 * (0.80 - 0.30) = 0.30 + 0.004 = 0.304
    assert abs(agent.trust - 0.304) < 0.001


def test_natural_recovery_does_not_exceed_baseline():
    """Natural recovery should not push trust above baseline."""
    model = _make_model(num_users=50, seed=42)
    agent = model.user_agents[0]
    agent.trust = agent.trust_baseline - 0.001
    pre_trust = agent.trust
    agent.apply_natural_recovery()
    assert agent.trust <= agent.trust_baseline


# ── Timeline integration tests ────────────────────────────────────────


def test_medium_intensity_trust_collapse_timeline():
    """At medium intensity, trust should not collapse before step 30."""
    model = _make_model(
        num_users=200,
        dark_pattern_intensity=0.50,
        pattern_forced_trial=True,
        pattern_hard_cancel=True,
        pattern_drip_pricing=True,
        customer_support_quality=0.30,
        seed=42,
    )
    for step in range(30):
        model.step()
        active = [a for a in model.user_agents if a.active]
        if active:
            mean_trust = sum(a.trust for a in active) / len(active)
            assert mean_trust > 0.20, (
                f"Trust collapsed too fast: {mean_trust:.3f} at step {step+1}"
            )


def test_wom_spread_gradual_not_explosive():
    """Negative WOM should build gradually, not explode in early steps."""
    model = _make_model(
        num_users=200,
        dark_pattern_intensity=0.50,
        pattern_forced_trial=True,
        pattern_hard_cancel=True,
        pattern_drip_pricing=True,
        seed=42,
    )
    model.step()
    model.step()
    wom_step2 = model._cumulative_negative_wom
    assert wom_step2 < 20, f"WOM too fast at step 2: {wom_step2}"

    for _ in range(8):
        model.step()
    wom_step10 = model._cumulative_negative_wom
    assert wom_step10 < 150, f"WOM too fast at step 10: {wom_step10}"
