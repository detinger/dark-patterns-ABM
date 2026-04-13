"""
User and Platform agents for the Dark-Matters ABM simulation.

UserAgent  -- heterogeneous consumer with type-driven attributes, detection
              logic, trust/harm dynamics, and word-of-mouth behaviour.
PlatformAgent -- single platform operator with adaptive strategy.
"""

from __future__ import annotations

import math
import mesa

from app.simulation.config import (
    DEFAULT_TYPE_DISTRIBUTION,
    USER_TYPE_RANGES,
    DARK_PATTERN_DEFAULTS,
    ALPHA_EXPOSURE_TO_TRUST,
    BETA_SUPPORT_RECOVERY,
    DELTA_EXPOSURE_TO_HARM,
    GAMMA_SOCIAL_TRUST_LOSS,
    THETA0,
    THETA_TRUST,
    THETA_HARM,
    THETA_SOCIAL,
    THETA_SWITCHING_COST,
    NEGATIVE_WOM_DECAY_RATE,
    POSITIVE_WOM_DECAY_RATE,
    WOM_AWARENESS_BOOST,
    WOM_TRUST_PENALTY,
    POSITIVE_WOM_TRUST_BOOST,
    POSITIVE_WOM_BASE_RATE,
    WOM_COOLDOWN_PERIOD,
    SATISFIED_TRUST_THRESHOLD,
    EXIT_WOM_HARM_THRESHOLD,
    REVIEW_VISIBILITY,
    CHURN_ADAPTATION_THRESHOLD,
    ADAPTATION_INTENSITY_REDUCTION,
    ADAPTATION_SUPPORT_BOOST,
    ADAPTATION_INTENSITY_INCREASE,
)
from app.simulation.patterns import (
    DarkPattern,
    calculate_exposure,
    calculate_detection,
    calculate_harm,
)


# ── Utility ────────────────────────────────────────────────────────────


def clamp(x: float, lo: float = 0.0, hi: float = 1.0) -> float:
    """Clamp *x* to the closed interval [lo, hi]."""
    return max(lo, min(hi, x))


# ── UserAgent ──────────────────────────────────────────────────────────


class UserAgent(mesa.Agent):
    """Heterogeneous consumer agent with type-driven attributes."""

    def __init__(self, model: mesa.Model) -> None:
        super().__init__(model)
        rng = self.random

        # ── Assign user type from model's distribution ─────────────
        type_dist: dict[str, float] = getattr(
            model, "type_distribution", DEFAULT_TYPE_DISTRIBUTION
        )
        types = list(type_dist.keys())
        weights = list(type_dist.values())
        self.user_type: str = rng.choices(types, weights=weights, k=1)[0]

        # ── Sample attributes from USER_TYPE_RANGES ────────────────
        ranges = USER_TYPE_RANGES[self.user_type]

        self.trust_baseline: float = rng.uniform(*ranges["trust_baseline"])
        self.digital_literacy: float = rng.uniform(*ranges["digital_literacy"])
        self.manipulation_sensitivity: float = rng.uniform(
            *ranges["manipulation_sensitivity"]
        )
        self.social_activity: float = rng.uniform(*ranges["social_activity"])
        self.complaint_propensity: float = rng.uniform(
            *ranges["complaint_propensity"]
        )
        self.switching_cost: float = rng.uniform(*ranges["switching_cost"])

        # ── Per-pattern sensitivity ────────────────────────────────
        sens_range = ranges["pattern_sensitivity"]
        self.pattern_sensitivity: dict[str, float] = {
            pname: rng.uniform(*sens_range)
            for pname in DARK_PATTERN_DEFAULTS
        }

        # ── Dynamic state ──────────────────────────────────────────
        self.trust: float = self.trust_baseline
        self.perceived_fairness: float = self.trust_baseline
        self.harm: float = 0.0
        self.negative_wom: float = 0.0
        self.active: bool = True
        self.network_id: int | None = None

        # ── Detection tracking ─────────────────────────────────────
        self.warning_awareness: float = 0.0
        self.positive_sentiment: float = 0.0
        self.last_negative_wom_received_step: int = -(WOM_COOLDOWN_PERIOD + 1)
        self.exposure_count: int = 0
        self.cumulative_exposure: float = 0.0

        # ── Event counters ─────────────────────────────────────────
        self.detected_events: dict[str, int] = {
            pname: 0 for pname in DARK_PATTERN_DEFAULTS
        }
        self.negative_wom_sent: int = 0
        self.negative_wom_received: int = 0
        self.positive_wom_sent: int = 0
        self.positive_wom_received: int = 0
        self.received_negative_signal: float = 0.0

        # ── Per-step scratch ───────────────────────────────────────
        self._step_detected_patterns: list[str] = []
        self._step_total_harm: float = 0.0

        # ── Reporting ──────────────────────────────────────────────
        self.last_exposure: float = 0.0
        self.last_churn_probability: float = 0.0
        self.last_review_valence: float = 0.0

    # ── Exposure / Detection / Harm ────────────────────────────────

    def apply_direct_exposure(
        self, pattern: DarkPattern, intensity: float
    ) -> bool:
        """Process one dark-pattern exposure for this agent.

        Returns *True* if the agent detected the pattern.
        """
        if not self.active:
            return False

        rng = self.model.random

        # 1. Exposure check
        exposed = calculate_exposure(intensity, rng=rng)
        if not exposed:
            return False

        self.exposure_count += 1
        self.cumulative_exposure += intensity

        # 2. Detection check
        detected = calculate_detection(
            digital_literacy=self.digital_literacy,
            detectability=pattern.detectability,
            warning_awareness=self.warning_awareness,
            rng=rng,
        )

        if detected:
            self.detected_events[pattern.name] = (
                self.detected_events.get(pattern.name, 0) + 1
            )
            self._step_detected_patterns.append(pattern.name)

        # 3. Harm calculation (0-100 scale from calculate_harm)
        agent_sensitivity = self.pattern_sensitivity.get(pattern.name, 1.0)
        harm = calculate_harm(pattern, intensity, detected, agent_sensitivity)
        scaled_harm = harm / 100.0

        self.last_exposure = scaled_harm
        self._step_total_harm += scaled_harm

        # 4. Trust loss  (doc formula)
        alpha = ALPHA_EXPOSURE_TO_TRUST
        detection_multiplier = 0.6 + 0.8 * self.digital_literacy
        trust_loss = (
            alpha
            * scaled_harm
            * self.manipulation_sensitivity
            * detection_multiplier
        )

        # 5. Harm accumulation  (doc formula)
        delta = DELTA_EXPOSURE_TO_HARM
        harm_gain = delta * scaled_harm * (0.7 + 0.6 * self.manipulation_sensitivity)

        # 6. Update state
        self.trust = clamp(self.trust - trust_loss)
        self.perceived_fairness = clamp(self.perceived_fairness - 0.8 * trust_loss)
        self.harm += harm_gain
        self.last_review_valence = -min(1.0, scaled_harm)

        return detected

    # ── Social signal ──────────────────────────────────────────────

    def apply_social_signal(self) -> None:
        """Apply accumulated negative social signals to trust."""
        if not self.active:
            return
        social_loss = GAMMA_SOCIAL_TRUST_LOSS * self.received_negative_signal
        self.trust = clamp(self.trust - social_loss)
        self.perceived_fairness = clamp(
            self.perceived_fairness - 0.8 * social_loss
        )
        self.received_negative_signal = 0.0

    # ── Recovery ───────────────────────────────────────────────────

    def apply_recovery(self) -> None:
        """Partial trust recovery via customer support."""
        if not self.active:
            return
        support_quality = self.model.platform.customer_support_quality
        recovery = (
            BETA_SUPPORT_RECOVERY * support_quality * (1.0 - self.harm * 0.15)
        )
        recovery = max(0.0, recovery)
        self.trust = min(self.trust_baseline, clamp(self.trust + recovery))
        self.perceived_fairness = clamp(
            self.perceived_fairness + 0.7 * recovery
        )

    # ── Word of Mouth ──────────────────────────────────────────────

    def decide_word_of_mouth(self) -> float:
        """Compute negative WOM propensity and cache it."""
        if not self.active:
            self.negative_wom = 0.0
            return 0.0
        base = (
            0.20 * self.social_activity
            + 0.35 * self.complaint_propensity
            + 0.30 * min(1.0, self.harm)
            + 0.15 * (1.0 - self.trust)
        )
        self.negative_wom = clamp(base)
        return self.negative_wom

    def spread_negative_wom(
        self, graph, social_influence_strength: float
    ) -> list[dict]:
        """Spread negative word-of-mouth to active neighbours.

        Returns a list of ``{source, target, intensity}`` edge dicts.
        """
        edges: list[dict] = []
        if not self.active or self.network_id is None:
            return edges

        rng = self.model.random
        neighbors = list(graph.neighbors(self.network_id))

        for nbr_id in neighbors:
            nbr = self.model.user_by_network.get(nbr_id)
            if nbr is None or not nbr.active:
                continue

            wom_prob = self.social_activity * self.complaint_propensity
            if rng.random() >= wom_prob:
                continue

            # Boost neighbour warning awareness (diminishing returns)
            nbr.warning_awareness = min(
                1.0,
                nbr.warning_awareness
                + WOM_AWARENESS_BOOST * (1.0 - nbr.warning_awareness),
            )
            # Penalise neighbour trust
            nbr.trust = clamp(
                nbr.trust - WOM_TRUST_PENALTY * social_influence_strength
            )
            # Signal + counters
            nbr.received_negative_signal += 1.0
            nbr.negative_wom_received += 1
            self.negative_wom_sent += 1

            edges.append(
                {
                    "source": self.network_id,
                    "target": nbr_id,
                    "intensity": self.negative_wom,
                }
            )

        return edges

    def spread_positive_wom(
        self, graph, social_influence_strength: float
    ) -> None:
        """Spread positive word-of-mouth to active neighbours."""
        if not self.active or self.network_id is None:
            return

        rng = self.model.random
        pos_prob = POSITIVE_WOM_BASE_RATE * self.social_activity * self.trust
        neighbors = list(graph.neighbors(self.network_id))

        for nbr_id in neighbors:
            nbr = self.model.user_by_network.get(nbr_id)
            if nbr is None or not nbr.active:
                continue

            if rng.random() >= pos_prob:
                continue

            # Boost positive sentiment (diminishing returns)
            nbr.positive_sentiment = min(
                1.0,
                nbr.positive_sentiment
                + POSITIVE_WOM_TRUST_BOOST * (1.0 - nbr.positive_sentiment),
            )
            # Boost trust capped at baseline
            nbr.trust = min(
                nbr.trust_baseline,
                clamp(
                    nbr.trust
                    + POSITIVE_WOM_TRUST_BOOST * social_influence_strength
                ),
            )
            # Counters
            nbr.positive_wom_received += 1
            self.positive_wom_sent += 1

    # ── Churn ──────────────────────────────────────────────────────

    def compute_churn_probability(self) -> float:
        """Logistic churn model from the doc."""
        if not self.active:
            self.last_churn_probability = 1.0
            return 1.0

        z = (
            THETA0
            + THETA_TRUST * (1.0 - self.trust)
            + THETA_HARM * self.harm
            + THETA_SOCIAL * self.negative_wom
            - THETA_SWITCHING_COST * self.switching_cost
        )
        p = 1.0 / (1.0 + math.exp(-z))
        self.last_churn_probability = clamp(p)
        return self.last_churn_probability

    def maybe_churn(self) -> bool:
        """Probabilistically churn.  Returns *True* if the agent churned."""
        if self.active and self.random.random() < self.compute_churn_probability():
            self.active = False
            return True
        return False

    # ── Snapshot / step ────────────────────────────────────────────

    def to_snapshot(self) -> dict:
        """Return a serialisable summary of this agent's state."""
        return {
            "id": self.unique_id,
            "user_type": self.user_type,
            "trust": round(self.trust, 4),
            "perceived_fairness": round(self.perceived_fairness, 4),
            "harm": round(self.harm, 4),
            "negative_wom": round(self.negative_wom, 4),
            "active": self.active,
            "last_exposure": round(self.last_exposure, 4),
            "last_churn_probability": round(self.last_churn_probability, 4),
            "warning_awareness": round(self.warning_awareness, 4),
        }

    def step(self) -> None:
        """No-op -- orchestrated by the model's step()."""
        pass


# ── PlatformAgent ──────────────────────────────────────────────────────


class PlatformAgent(mesa.Agent):
    """Single platform operator that may adapt its strategy."""

    def __init__(
        self,
        model: mesa.Model,
        dark_pattern_intensity: float,
        customer_support_quality: float,
        adaptive_platform: bool,
    ) -> None:
        super().__init__(model)
        self.dark_pattern_intensity: float = clamp(dark_pattern_intensity)
        self.customer_support_quality: float = clamp(customer_support_quality)
        self.adaptive_platform: bool = adaptive_platform
        self.reputation: float = 1.0
        self.short_term_revenue: float = 0.0
        self.long_term_revenue: float = 0.0

    def adapt_strategy(self) -> None:
        """Adjust intensity / support based on churn and reputation."""
        if not self.adaptive_platform:
            return

        if (
            self.model.churn_rate > CHURN_ADAPTATION_THRESHOLD
            or self.reputation < 0.45
        ):
            self.dark_pattern_intensity = clamp(
                self.dark_pattern_intensity - ADAPTATION_INTENSITY_REDUCTION
            )
            self.customer_support_quality = clamp(
                self.customer_support_quality + ADAPTATION_SUPPORT_BOOST
            )
        elif self.model.churn_rate < 0.03 and self.reputation > 0.70:
            self.dark_pattern_intensity = clamp(
                self.dark_pattern_intensity + ADAPTATION_INTENSITY_INCREASE
            )
