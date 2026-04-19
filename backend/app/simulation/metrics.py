"""
Data-collector reporter functions for the Dark-Matters ABM.

Every public function in this module takes a *model* instance and returns
a single scalar value suitable for Mesa's ``DataCollector``.

``build_all_reporters()`` assembles all reporters into one dict that can
be passed straight to ``DataCollector(model_reporters=...)``.

Reporter categories
-------------------
1. Aggregate metrics  (25 functions)
2. Tipping-point reporters  (8 per-point + 3 summary = 11)
3. Per-user-type reporters  (4 metrics x 3 types = 12, via factories)
4. Per-dark-pattern reporters  (3 metrics x 3 patterns = 9, via factories)

Total: 57 reporters (with default config).
"""

from __future__ import annotations

from app.simulation.config import DEFAULT_TYPE_DISTRIBUTION, DARK_PATTERN_DEFAULTS

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _active(model):
    """Return the list of active user agents."""
    return [a for a in model.user_agents if a.active]


def _safe_mean(values: list[float]) -> float:
    """Return the arithmetic mean, or 0.0 for an empty sequence."""
    return sum(values) / len(values) if values else 0.0


# ── 1. Aggregate metric functions ─────────────────────────────────────────

def active_users(model) -> int:
    """Count of active user agents."""
    return sum(1 for a in model.user_agents if a.active)


def mean_trust(model) -> float:
    """Mean trust of *active* users."""
    return _safe_mean([a.trust for a in model.user_agents if a.active])


def mean_trust_all(model) -> float:
    """Mean trust of ALL users (active and churned)."""
    return _safe_mean([a.trust for a in model.user_agents])


def mean_harm(model) -> float:
    """Mean harm of active users."""
    return _safe_mean([a.harm for a in model.user_agents if a.active])


def churn_rate(model) -> float:
    return model.churn_rate


def cumulative_churn(model) -> float:
    return model.cumulative_churn


def reputation(model) -> float:
    return model.platform.reputation


def short_term_revenue(model) -> float:
    return model.platform.short_term_revenue


def long_term_revenue(model) -> float:
    return model.platform.long_term_revenue


def negative_wom_rate(model) -> float:
    """Mean negative_wom of active users."""
    return _safe_mean([a.negative_wom for a in model.user_agents if a.active])


def step_churns(model) -> int:
    return model._step_churns


def step_negative_wom_count(model) -> int:
    return model._step_negative_wom


def step_positive_wom_count(model) -> int:
    return model._step_positive_wom


def cumulative_negative_wom_count(model) -> int:
    return model._cumulative_negative_wom


def cumulative_positive_wom_count(model) -> int:
    return model._cumulative_positive_wom


def avg_warning_awareness(model) -> float:
    """Mean warning_awareness of active users."""
    return _safe_mean([a.warning_awareness for a in model.user_agents if a.active])


def avg_positive_sentiment(model) -> float:
    """Mean positive_sentiment of active users."""
    return _safe_mean([a.positive_sentiment for a in model.user_agents if a.active])


def customer_support_quality(model) -> float:
    return model.platform.customer_support_quality


def platform_reputation(model) -> float:
    """Detailed platform reputation (model-level, distinct from platform.reputation)."""
    return model.platform_reputation


def step_base_revenue(model) -> float:
    """Per-step subscription revenue from active users."""
    return model._step_base_revenue


def step_dp_revenue(model) -> float:
    """Per-step dark-pattern extraction revenue (detected + hidden)."""
    return model._step_dp_revenue


def step_revenue(model) -> float:
    return model._step_revenue


def step_costs(model) -> float:
    return model._step_costs


def step_profit(model) -> float:
    return model._step_profit


def cumulative_revenue(model) -> float:
    return model._cumulative_revenue


def cumulative_costs(model) -> float:
    return model._cumulative_costs


def net_value(model) -> float:
    return model._net_value


def cumulative_projected_revenue(model) -> float:
    return model._cumulative_projected_revenue


def opportunity_cost(model) -> float:
    return model._opportunity_cost


# ── 2. Tipping-point reporters ────────────────────────────────────────────

_TIPPING_POINT_NAMES = [
    "trust_collapse",
    "social_contagion",
    "churn_cascade",
    "extractive_divergence",
]


def trust_collapse_triggered(model) -> float:
    return float(model.tipping_points["trust_collapse"]["triggered"])


def trust_collapse_step(model) -> int:
    step = model.tipping_points["trust_collapse"]["step"]
    return -1 if step is None else step


def social_contagion_triggered(model) -> float:
    return float(model.tipping_points["social_contagion"]["triggered"])


def social_contagion_step(model) -> int:
    step = model.tipping_points["social_contagion"]["step"]
    return -1 if step is None else step


def churn_cascade_triggered(model) -> float:
    return float(model.tipping_points["churn_cascade"]["triggered"])


def churn_cascade_step(model) -> int:
    step = model.tipping_points["churn_cascade"]["step"]
    return -1 if step is None else step


def extractive_divergence_triggered(model) -> float:
    return float(model.tipping_points["extractive_divergence"]["triggered"])


def extractive_divergence_step(model) -> int:
    step = model.tipping_points["extractive_divergence"]["step"]
    return -1 if step is None else step


def tipping_points_triggered_count(model) -> int:
    return sum(1 for point in model.tipping_points.values() if point["triggered"])


def any_tipping_point_triggered(model) -> float:
    return float(tipping_points_triggered_count(model) > 0)


def first_tipping_point_step(model) -> int:
    steps = [
        point["step"]
        for point in model.tipping_points.values()
        if point["step"] is not None
    ]
    return -1 if not steps else min(steps)


# ── 3. Factory functions for per-type reporters ──────────────────────────

def _make_type_trust_reporter(utype: str):
    """Return a reporter for mean trust of active agents of *utype*."""

    def _reporter(model) -> float:
        vals = [a.trust for a in model.user_agents if a.active and a.user_type == utype]
        return _safe_mean(vals)

    _reporter.__name__ = f"trust_{utype}"
    _reporter.__doc__ = f"Mean trust of active {utype} agents."
    return _reporter


def _make_type_churn_reporter(utype: str):
    """Return a reporter for count of churned agents of *utype*."""

    def _reporter(model) -> int:
        return sum(
            1 for a in model.user_agents if not a.active and a.user_type == utype
        )

    _reporter.__name__ = f"churned_{utype}"
    _reporter.__doc__ = f"Count of churned {utype} agents."
    return _reporter


def _make_type_neg_wom_reporter(utype: str):
    """Return a reporter for total negative_wom_sent of *utype*."""

    def _reporter(model) -> float:
        return sum(
            a.negative_wom_sent
            for a in model.user_agents
            if a.user_type == utype
        )

    _reporter.__name__ = f"neg_wom_sent_{utype}"
    _reporter.__doc__ = f"Total negative WOM sent by {utype} agents."
    return _reporter


def _make_type_pos_wom_reporter(utype: str):
    """Return a reporter for total positive_wom_sent of *utype*."""

    def _reporter(model) -> float:
        return sum(
            a.positive_wom_sent
            for a in model.user_agents
            if a.user_type == utype
        )

    _reporter.__name__ = f"pos_wom_sent_{utype}"
    _reporter.__doc__ = f"Total positive WOM sent by {utype} agents."
    return _reporter


# ── 4. Factory functions for per-pattern reporters ───────────────────────

def _make_pattern_detection_reporter(pname: str):
    """Return a reporter for step detection count of pattern *pname*."""

    def _reporter(model) -> int:
        return model._step_detections_by_pattern[pname]

    _reporter.__name__ = f"detections_{pname}"
    _reporter.__doc__ = f"Step-level detections of {pname}."
    return _reporter


def _make_pattern_trust_loss_reporter(pname: str):
    """Return a reporter for step trust loss caused by pattern *pname*."""

    def _reporter(model) -> float:
        return model._step_trust_loss_by_pattern[pname]

    _reporter.__name__ = f"trust_loss_{pname}"
    _reporter.__doc__ = f"Step-level trust loss from {pname}."
    return _reporter


def _make_pattern_exposure_reporter(pname: str):
    """Return a reporter for step exposure count of pattern *pname*."""

    def _reporter(model) -> int:
        return model._step_exposure_count_by_pattern[pname]

    _reporter.__name__ = f"exposures_{pname}"
    _reporter.__doc__ = f"Step-level exposure count for {pname}."
    return _reporter


# ── 5. build_all_reporters() ─────────────────────────────────────────────

def build_all_reporters() -> dict[str, callable]:
    """
    Return a dict of **all** reporter functions, keyed by metric name.

    The dict is ready for ``DataCollector(model_reporters=build_all_reporters())``.
    With the default config (3 user types, 3 dark patterns) this produces 57
    reporters.
    """
    reporters: dict[str, callable] = {}

    # -- Aggregate metrics (25) ------------------------------------------------
    reporters["active_users"] = active_users
    reporters["mean_trust"] = mean_trust
    reporters["mean_trust_all"] = mean_trust_all
    reporters["mean_harm"] = mean_harm
    reporters["churn_rate"] = churn_rate
    reporters["cumulative_churn"] = cumulative_churn
    reporters["reputation"] = reputation
    reporters["short_term_revenue"] = short_term_revenue
    reporters["long_term_revenue"] = long_term_revenue
    reporters["negative_wom_rate"] = negative_wom_rate
    reporters["step_churns"] = step_churns
    reporters["step_negative_wom_count"] = step_negative_wom_count
    reporters["step_positive_wom_count"] = step_positive_wom_count
    reporters["cumulative_negative_wom_count"] = cumulative_negative_wom_count
    reporters["cumulative_positive_wom_count"] = cumulative_positive_wom_count
    reporters["avg_warning_awareness"] = avg_warning_awareness
    reporters["avg_positive_sentiment"] = avg_positive_sentiment
    reporters["customer_support_quality"] = customer_support_quality
    reporters["platform_reputation"] = platform_reputation
    reporters["step_base_revenue"] = step_base_revenue
    reporters["step_dp_revenue"] = step_dp_revenue
    reporters["step_revenue"] = step_revenue
    reporters["step_costs"] = step_costs
    reporters["step_profit"] = step_profit
    reporters["cumulative_revenue"] = cumulative_revenue
    reporters["cumulative_costs"] = cumulative_costs
    reporters["net_value"] = net_value
    reporters["cumulative_projected_revenue"] = cumulative_projected_revenue
    reporters["opportunity_cost"] = opportunity_cost

    # -- Tipping-point reporters (8 + 3 = 11) ----------------------------------
    reporters["trust_collapse_triggered"] = trust_collapse_triggered
    reporters["trust_collapse_step"] = trust_collapse_step
    reporters["social_contagion_triggered"] = social_contagion_triggered
    reporters["social_contagion_step"] = social_contagion_step
    reporters["churn_cascade_triggered"] = churn_cascade_triggered
    reporters["churn_cascade_step"] = churn_cascade_step
    reporters["extractive_divergence_triggered"] = extractive_divergence_triggered
    reporters["extractive_divergence_step"] = extractive_divergence_step
    reporters["tipping_points_triggered_count"] = tipping_points_triggered_count
    reporters["any_tipping_point_triggered"] = any_tipping_point_triggered
    reporters["first_tipping_point_step"] = first_tipping_point_step

    # -- Per-user-type reporters (4 x len(DEFAULT_TYPE_DISTRIBUTION) = 12) -----
    for utype in DEFAULT_TYPE_DISTRIBUTION:
        reporters[f"trust_{utype}"] = _make_type_trust_reporter(utype)
        reporters[f"churned_{utype}"] = _make_type_churn_reporter(utype)
        reporters[f"neg_wom_sent_{utype}"] = _make_type_neg_wom_reporter(utype)
        reporters[f"pos_wom_sent_{utype}"] = _make_type_pos_wom_reporter(utype)

    # -- Per-dark-pattern reporters (3 x len(DARK_PATTERN_DEFAULTS) = 9) -------
    for pname in DARK_PATTERN_DEFAULTS:
        reporters[f"detections_{pname}"] = _make_pattern_detection_reporter(pname)
        reporters[f"trust_loss_{pname}"] = _make_pattern_trust_loss_reporter(pname)
        reporters[f"exposures_{pname}"] = _make_pattern_exposure_reporter(pname)

    return reporters