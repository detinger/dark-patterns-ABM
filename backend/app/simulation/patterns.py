"""
Dark-pattern definitions with pure detection / harm calculations.

Every function in this module is a pure calculation (no side effects).
The optional ``rng`` parameter accepts the model's seeded ``random.Random``
instance for reproducibility; when *None* it falls back to stdlib ``random``.
"""

from __future__ import annotations

import random
from dataclasses import dataclass

from app.simulation.config import (
    DARK_PATTERN_DEFAULTS,
    DETECTION_NOISE_SCALE,
    EXPOSURE_NOISE_SCALE,
    MAX_DETECTION_PROBABILITY,
)


@dataclass(frozen=True)
class DarkPattern:
    """Immutable descriptor for a single dark-pattern type."""

    name: str
    intensity: float
    detectability: float
    base_harm: float
    detected_harm_multiplier: float
    hidden_harm_multiplier: float
    wom_propensity_multiplier: float
    short_term_gain_weight: float

    @classmethod
    def from_config(cls, name: str, intensity: float) -> DarkPattern:
        """Build a *DarkPattern* from :data:`DARK_PATTERN_DEFAULTS`.

        Parameters
        ----------
        name:
            Key into ``DARK_PATTERN_DEFAULTS`` (e.g. ``"drip_pricing"``).
        intensity:
            Global intensity scalar supplied by the scenario / model.

        Raises
        ------
        KeyError
            If *name* is not found in ``DARK_PATTERN_DEFAULTS``.
        """
        defaults = DARK_PATTERN_DEFAULTS[name]
        return cls(
            name=name,
            intensity=intensity,
            detectability=defaults["detectability"],
            base_harm=defaults["base_harm"],
            detected_harm_multiplier=defaults["detected_harm_multiplier"],
            hidden_harm_multiplier=defaults["hidden_harm_multiplier"],
            wom_propensity_multiplier=defaults["wom_propensity_multiplier"],
            short_term_gain_weight=defaults["short_term_gain_weight"],
        )


# ── Pure calculation helpers ───────────────────────────────────────────


def calculate_exposure(intensity: float, rng: random.Random | None = None) -> bool:
    """Return *True* if the agent is exposed this step.

    A uniform draw is compared against ``intensity + noise``.
    """
    r = rng if rng else random
    noise = r.uniform(-EXPOSURE_NOISE_SCALE, EXPOSURE_NOISE_SCALE)
    return r.random() < max(0.0, intensity + noise)


def calculate_detection(
    digital_literacy: float,
    detectability: float,
    warning_awareness: float,
    rng: random.Random | None = None,
) -> bool:
    """Return *True* if the agent detects the dark pattern.

    Detection probability is capped at :data:`MAX_DETECTION_PROBABILITY`.
    """
    r = rng if rng else random
    noise = r.uniform(-DETECTION_NOISE_SCALE, DETECTION_NOISE_SCALE)
    raw_prob = digital_literacy * detectability * (1.0 + warning_awareness) + noise
    detect_prob = max(0.0, min(raw_prob, MAX_DETECTION_PROBABILITY))
    return r.random() < detect_prob


def calculate_harm(
    pattern: DarkPattern,
    intensity: float,
    detected: bool,
    agent_sensitivity: float,
) -> float:
    """Compute the harm inflicted on an agent by a dark pattern.

    Returns 0.0 when *intensity* is non-positive.  Otherwise the value is::

        base_harm * intensity * multiplier * agent_sensitivity

    where *multiplier* is ``detected_harm_multiplier`` when the agent noticed
    the pattern, or ``hidden_harm_multiplier`` when it went undetected.
    """
    if intensity <= 0.0:
        return 0.0
    multiplier = (
        pattern.detected_harm_multiplier if detected else pattern.hidden_harm_multiplier
    )
    return pattern.base_harm * intensity * multiplier * agent_sensitivity
