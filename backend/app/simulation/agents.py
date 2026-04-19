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
    BETA_SHAPE,
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
    EXPOSURE_BUILDUP_STEPS,
    INITIAL_HARM_FRACTION,
    HARM_DAMPENING_FACTOR,
    HARM_DAMPENING_CAP,
    WOM_HARM_COOLDOWN_THRESHOLD,
    WOM_RAMP_RANGE,
    WOM_DAMPING_FACTOR,
    WOM_MAX_NEIGHBORS_PER_STEP,
    WOM_DIMINISHING_RATE,
    WOM_TRUST_SHIELD,
    RECOVERY_EXPOSURE_CEILING,
    NATURAL_TRUST_RECOVERY,
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


def beta_sample(rng, low: float, high: float, shape: float = BETA_SHAPE) -> float:
    """Draw from Beta(shape, shape) scaled to [low, high].

    Symmetric bell shape — concentrates mass around the midpoint, with
    rare extreme values.  Higher *shape* values tighten the distribution.
    """
    raw = rng.betavariate(shape, shape)
    return low + raw * (high - low)


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

        # ── Sample attributes from USER_TYPE_RANGES (Beta distribution) ─
        ranges = USER_TYPE_RANGES[self.user_type]

        self.trust_baseline: float = beta_sample(rng, *ranges["trust_baseline"])
        self.digital_literacy: float = beta_sample(rng, *ranges["digital_literacy"])
        self.manipulation_sensitivity: float = beta_sample(
            rng, *ranges["manipulation_sensitivity"]
        )
        self.social_activity: float = beta_sample(rng, *ranges["social_activity"])
        self.complaint_propensity: float = beta_sample(
            rng, *ranges["complaint_propensity"]
        )
        self.switching_cost: float = beta_sample(rng, *ranges["switching_cost"])
        self.trust_resilience: float = beta_sample(rng, *ranges["trust_resilience"])

        # ── Per-pattern sensitivity ────────────────────────────────
        sens_range = ranges["pattern_sensitivity"]
        self.pattern_sensitivity: dict[str, float] = {
            pname: beta_sample(rng, *sens_range)
            for pname in DARK_PATTERN_DEFAULTS
        }

        # ── Dynamic state ──────────────────────────────────────────
        self.trust: float = self.trust_baseline
        self.perceived_fairness: float = self.trust_baseline
        self.harm: float = 0.0
        self.negative_wom: float = 0.0
        self.active: bool = True
        self.network_id: int | None = None
        self._wom_ramp_factor: float = 0.0

        # ── Detection tracking ─────────────────────────────────────
        self.warning_awareness: float = 0.0
        self.positive_sentiment: float = 0.0
        self.last_negative_wom_received_step: int = -(WOM_COOLDOWN_PERIOD + 1)
        self.exposure_count: int = 0
        self.cumulative_exposure: float = 0.0
        # Per-pattern exposure counts drive the buildup ramp
        self.pattern_exposure_count: dict[str, int] = {
            pname: 0 for pname in DARK_PATTERN_DEFAULTS
        }

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
        self._step_wom_received: int = 0

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
        self.pattern_exposure_count[pattern.name] = (
            self.pattern_exposure_count.get(pattern.name, 0) + 1
        )

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

        # Exposure buildup: first N encounters with a pattern deliver partial
        # harm while the agent habituates.  Full harm kicks in after buildup.
        pat_count = self.pattern_exposure_count[pattern.name]
        if pat_count < EXPOSURE_BUILDUP_STEPS:
            buildup_factor = (
                INITIAL_HARM_FRACTION
                + (1.0 - INITIAL_HARM_FRACTION) * (pat_count / EXPOSURE_BUILDUP_STEPS)
            )
            scaled_harm *= buildup_factor

        self.last_exposure = scaled_harm
        self._step_total_harm += scaled_harm

        # 4. Trust loss  (doc formula)
        # trust_resilience dampens loss for users who rationalise or fail
        # to attribute bad UX to dark patterns (primarily naive users).
        alpha = ALPHA_EXPOSURE_TO_TRUST
        detection_multiplier = 0.6 + 0.8 * self.digital_literacy
        trust_loss = (
            alpha
            * scaled_harm
            * self.manipulation_sensitivity
            * detection_multiplier
            * (1.0 - self.trust_resilience)
        )

        # 5. Harm accumulation  (doc formula + saturation)
        # Saturation factor max(0, 1-harm) means harm grows logistically:
        # full rate near 0, slowing as harm → 1.0, zero gain above 1.0.
        # This models desensitisation — users stop reacting to a bad platform
        # they've already internalised as normal.
        delta = DELTA_EXPOSURE_TO_HARM
        saturation = max(0.0, 1.0 - self.harm)
        harm_gain = delta * scaled_harm * (0.7 + 0.6 * self.manipulation_sensitivity) * saturation

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
        """Partial trust recovery via customer support (doc: β·R_i(t)).

        Recovery only applies when the user was NOT exposed to any dark
        pattern this step — it represents a positive platform experience
        (e.g. good customer support), not an unconditional drift.
        """
        if not self.active:
            return
        # No recovery if exposed this step
        if self._step_total_harm > 0:
            return
        support_quality = self.model.platform.customer_support_quality
        # Harm dampening: as cumulative harm grows, customer support is less
        # effective at rebuilding trust — captures desensitisation/cynicism.
        dampening = 1.0 - min(self.harm * HARM_DAMPENING_FACTOR, HARM_DAMPENING_CAP)
        recovery = BETA_SUPPORT_RECOVERY * support_quality * dampening
        recovery = max(0.0, recovery)
        self.trust = min(self.trust_baseline, clamp(self.trust + recovery))
        self.perceived_fairness = clamp(
            self.perceived_fairness + 0.7 * recovery
        )

    # ── Word of Mouth ──────────────────────────────────────────────

    def decide_word_of_mouth(self) -> float:
        """Compute negative WOM propensity with cooldown and ramp-up.

        Cooldown: users must accumulate harm >= WOM_HARM_COOLDOWN_THRESHOLD
        before generating any negative WOM.
        Ramp-up: once past cooldown, WOM scales gradually with harm.
        """
        if not self.active:
            self.negative_wom = 0.0
            self._wom_ramp_factor = 0.0
            return 0.0
        if self.harm < WOM_HARM_COOLDOWN_THRESHOLD:
            self.negative_wom = 0.0
            self._wom_ramp_factor = 0.0
            return 0.0
        ramp = min(
            1.0,
            (self.harm - WOM_HARM_COOLDOWN_THRESHOLD) / WOM_RAMP_RANGE,
        )
        self._wom_ramp_factor = ramp
        base = (
            0.10 * self.social_activity
            + 0.20 * self.complaint_propensity
            + 0.45 * min(1.0, self.harm)
            + 0.25 * (1.0 - self.trust)
        )
        self.negative_wom = clamp(base * ramp)
        return self.negative_wom

    def spread_negative_wom(
        self, graph, social_influence_strength: float, *, force: bool = False,
    ) -> list[dict]:
        """Spread negative word-of-mouth to active neighbours.

        Returns a list of ``{source, target, intensity}`` edge dicts.

        Parameters
        ----------
        force : bool
            If ``True``, skip the ``self.active`` check.  Used for exit WOM
            where the agent has just churned but still broadcasts a final
            negative signal.
        """
        edges: list[dict] = []
        if (not force and not self.active) or self.network_id is None:
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

        retention_bonus = getattr(self.model, "retention_bonus", 0.0)
        z = (
            THETA0
            + THETA_TRUST * (1.0 - self.trust)
            + THETA_HARM * self.harm
            + THETA_SOCIAL * self.negative_wom
            - THETA_SWITCHING_COST * self.switching_cost
            - retention_bonus
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

        platform_rep = self.model.platform_reputation
        if (
            self.model.churn_rate > CHURN_ADAPTATION_THRESHOLD
            or self.reputation < 0.55
            or platform_rep < 40.0
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
