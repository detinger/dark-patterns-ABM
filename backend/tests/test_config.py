"""Tests for app.simulation.config — constants, ranges, scenarios."""


def test_user_type_ranges_have_all_types():
    from app.simulation.config import USER_TYPE_RANGES
    assert set(USER_TYPE_RANGES.keys()) == {"skeptic", "naive", "activist"}


def test_user_type_ranges_have_required_fields():
    from app.simulation.config import USER_TYPE_RANGES
    required = {
        "trust_baseline", "digital_literacy", "manipulation_sensitivity",
        "social_activity", "complaint_propensity", "switching_cost",
        "pattern_sensitivity",
    }
    for utype, ranges in USER_TYPE_RANGES.items():
        assert required.issubset(set(ranges.keys())), f"{utype} missing fields"


def test_user_type_ranges_low_less_than_high():
    from app.simulation.config import USER_TYPE_RANGES
    for utype, ranges in USER_TYPE_RANGES.items():
        for field, (low, high) in ranges.items():
            assert low < high, f"{utype}.{field}: low={low} >= high={high}"


def test_dark_pattern_defaults_have_all_patterns():
    from app.simulation.config import DARK_PATTERN_DEFAULTS
    assert set(DARK_PATTERN_DEFAULTS.keys()) == {"forced_trial", "hard_cancel", "drip_pricing"}


def test_dark_pattern_defaults_have_required_fields():
    from app.simulation.config import DARK_PATTERN_DEFAULTS
    required = {
        "detectability", "base_harm", "detected_harm_multiplier",
        "hidden_harm_multiplier", "wom_propensity_multiplier",
        "short_term_gain_weight",
    }
    for name, props in DARK_PATTERN_DEFAULTS.items():
        assert required.issubset(set(props.keys())), f"{name} missing fields"


def test_scenarios_have_required_keys():
    from app.simulation.config import SCENARIOS
    required = {
        "patterns", "dark_pattern_intensity", "adaptive_platform",
        "customer_support_quality",
    }
    for name, scenario in SCENARIOS.items():
        assert required.issubset(set(scenario.keys())), f"Scenario {name} missing keys"


def test_control_scenario_has_zero_intensity():
    from app.simulation.config import SCENARIOS
    assert SCENARIOS["control"]["dark_pattern_intensity"] == 0.0
    for enabled in SCENARIOS["control"]["patterns"].values():
        assert enabled is False


def test_type_distribution_sums_to_one():
    from app.simulation.config import DEFAULT_TYPE_DISTRIBUTION
    assert abs(sum(DEFAULT_TYPE_DISTRIBUTION.values()) - 1.0) < 1e-9


def test_ten_scenarios_exist():
    from app.simulation.config import SCENARIOS
    assert len(SCENARIOS) == 10


def test_defaults_dict_has_required_keys():
    from app.simulation.config import DEFAULTS
    required = {
        "num_users", "network_type", "max_steps", "seed",
        "dark_pattern_intensity", "pattern_forced_trial",
        "customer_support_quality", "adaptive_platform",
    }
    assert required.issubset(set(DEFAULTS.keys()))


def test_all_named_constants_positive():
    from app.simulation.config import (
        DEFAULT_NUM_AGENTS, DEFAULT_MAX_STEPS, DEFAULT_AVG_NODE_DEGREE,
        TRUST_COLLAPSE_THRESHOLD, CHURN_ACCELERATION_THRESHOLD,
        WOM_BURST_THRESHOLD, TIPPING_POINT_PERSISTENCE,
        BASE_REVENUE_PER_USER, CHURN_REPLACEMENT_COST,
    )
    for val in [
        DEFAULT_NUM_AGENTS, DEFAULT_MAX_STEPS, DEFAULT_AVG_NODE_DEGREE,
        TRUST_COLLAPSE_THRESHOLD, CHURN_ACCELERATION_THRESHOLD,
        WOM_BURST_THRESHOLD, TIPPING_POINT_PERSISTENCE,
        BASE_REVENUE_PER_USER, CHURN_REPLACEMENT_COST,
    ]:
        assert val > 0
