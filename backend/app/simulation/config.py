"""
Combined configuration for the Dark-Matters ABM simulation.

All named constants live here — no magic numbers elsewhere.
Sections:
    1.  Model defaults
    2.  User-type distribution
    3.  User-type parameter ranges (uniform draws)
    4.  Dark-pattern profiles
    5.  Doc formula coefficients
    6.  Pattern exposure probabilities
    7.  Detection constants
    8.  WOM / diffusion constants
    9.  Platform economics
    10. Platform reputation
    11. Adaptation thresholds
    12. Tipping-point thresholds
    13. Scenario presets (10 scenarios)
    14. DEFAULTS dict (backward compat with FastAPI service)
"""

from __future__ import annotations

# ── 1. Model defaults ───────────────────────────────────────────────

DEFAULT_NUM_AGENTS = 500
DEFAULT_MAX_STEPS = 104  # 2 years, 1 step = 1 week
DEFAULT_AVG_NODE_DEGREE = 8
DEFAULT_REWIRING_PROB = 0.08
DEFAULT_NETWORK_TYPE = "small_world"
DEFAULT_SOCIAL_INFLUENCE_STRENGTH = 0.18

# ── 2. User-type distribution ───────────────────────────────────────

DEFAULT_TYPE_DISTRIBUTION: dict[str, float] = {
    "skeptic": 0.30,
    "naive": 0.50,
    "activist": 0.20,
}

# ── 3. User-type parameter ranges (uniform low, high) ──────────────
#
# Each sub-dict maps trait → (low, high) for a uniform draw.
# Traits: trust_baseline, digital_literacy, manipulation_sensitivity,
#          social_activity, complaint_propensity, switching_cost,
#          pattern_sensitivity.

USER_TYPE_RANGES: dict[str, dict[str, tuple[float, float]]] = {
    "skeptic": {
        "trust_baseline": (0.55, 0.70),
        "digital_literacy": (0.70, 0.95),
        "manipulation_sensitivity": (0.55, 0.75),
        "social_activity": (0.30, 0.50),
        "complaint_propensity": (0.40, 0.65),
        "switching_cost": (0.30, 0.45),
        "pattern_sensitivity": (1.0, 1.4),
    },
    "naive": {
        "trust_baseline": (0.75, 0.90),
        "digital_literacy": (0.15, 0.40),
        "manipulation_sensitivity": (0.30, 0.50),
        "social_activity": (0.10, 0.30),
        "complaint_propensity": (0.10, 0.25),
        "switching_cost": (0.50, 0.70),
        "pattern_sensitivity": (0.6, 0.9),
    },
    "activist": {
        "trust_baseline": (0.60, 0.75),
        "digital_literacy": (0.75, 0.95),
        "manipulation_sensitivity": (0.70, 0.90),
        "social_activity": (0.70, 0.95),
        "complaint_propensity": (0.60, 0.85),
        "switching_cost": (0.25, 0.40),
        "pattern_sensitivity": (1.1, 1.5),
    },
}

# ── 4. Dark-pattern profiles ────────────────────────────────────────

DARK_PATTERN_DEFAULTS: dict[str, dict[str, float]] = {
    "forced_trial": {
        "detectability": 0.3,
        "base_harm": 1.8,
        "detected_harm_multiplier": 2.2,
        "hidden_harm_multiplier": 0.8,
        "wom_propensity_multiplier": 1.6,
        "short_term_gain_weight": 1.6,
    },
    "hard_cancel": {
        "detectability": 0.4,
        "base_harm": 1.6,
        "detected_harm_multiplier": 2.0,
        "hidden_harm_multiplier": 0.5,
        "wom_propensity_multiplier": 1.3,
        "short_term_gain_weight": 1.0,
    },
    "drip_pricing": {
        "detectability": 0.4,
        "base_harm": 2.0,
        "detected_harm_multiplier": 2.0,
        "hidden_harm_multiplier": 0.5,
        "wom_propensity_multiplier": 1.3,
        "short_term_gain_weight": 1.0,
    },
}

# ── 5. Doc formula coefficients ─────────────────────────────────────

ALPHA_EXPOSURE_TO_TRUST = 0.22
BETA_SUPPORT_RECOVERY = 0.10
DELTA_EXPOSURE_TO_HARM = 0.18
GAMMA_SOCIAL_TRUST_LOSS = 0.12

THETA0 = -6.20              # baseline intercept (~0.1% weekly churn at healthy trust → ~90% retained over 2yr)
THETA_TRUST = 3.50          # weight of trust deficit (1 - T)
THETA_HARM = 2.50           # weight of cumulative harm
THETA_SOCIAL = 1.50         # weight of negative WOM exposure
THETA_SWITCHING_COST = 1.80 # protective effect of switching costs

# ── 6. Pattern exposure probabilities (scaled by global intensity) ──

FORCED_TRIAL_EXPOSURE_PROB = 0.12
FORCED_TRIAL_SEVERITY = 0.45

HARD_CANCEL_EXPOSURE_PROB = 0.10
HARD_CANCEL_SEVERITY = 0.50

DRIP_PRICING_EXPOSURE_PROB = 0.08
DRIP_PRICING_SEVERITY = 0.70

# ── 7. Detection constants ──────────────────────────────────────────

MAX_DETECTION_PROBABILITY = 0.95
DETECTION_NOISE_SCALE = 0.05
EXPOSURE_NOISE_SCALE = 0.05

# ── 8. WOM and diffusion constants ──────────────────────────────────

NEGATIVE_WOM_DECAY_RATE = 0.05
POSITIVE_WOM_DECAY_RATE = 0.10
WOM_AWARENESS_BOOST = 0.15
WOM_TRUST_PENALTY = 0.5
POSITIVE_WOM_TRUST_BOOST = 0.3
POSITIVE_WOM_BASE_RATE = 0.2
WOM_COOLDOWN_PERIOD = 5
SATISFIED_TRUST_THRESHOLD = 0.60
EXIT_WOM_HARM_THRESHOLD = 0.30
REVIEW_VISIBILITY = 0.35

# ── 9. Platform economics ───────────────────────────────────────────

BASE_REVENUE_PER_USER = 5.0
CHURN_REPLACEMENT_COST = 5.0
REPUTATION_DAMAGE_COST = 0.5
REFERRAL_VALUE = 0.3
SUPPORT_COST_RATE = 0.2
RETENTION_VALUE = 0.1

# ── 10. Platform reputation ─────────────────────────────────────────

DEFAULT_REPUTATION_RANGE: tuple[float, float] = (50, 70)
CHURN_REPUTATION_WEIGHT = 0.8
WOM_REPUTATION_WEIGHT = 0.06
POSITIVE_WOM_REPUTATION_WEIGHT = 0.03
REPUTATION_RECOVERY_RATE = 0.10
REPUTATION_NATURAL_CAP = 92.0

# ── 11. Adaptation thresholds ───────────────────────────────────────

CHURN_ADAPTATION_THRESHOLD = 0.08
WOM_ADAPTATION_THRESHOLD = 0.10
ADAPTATION_INTENSITY_REDUCTION = 0.04
ADAPTATION_SUPPORT_BOOST = 0.03
ADAPTATION_INTENSITY_INCREASE = 0.01

# ── 12. Tipping-point thresholds ────────────────────────────────────

TRUST_COLLAPSE_THRESHOLD = 0.03    # 3% trust drop per step signals collapse
CHURN_ACCELERATION_THRESHOLD = 0.03  # 3% of active users churn in a single step
WOM_BURST_THRESHOLD = 0.40         # 40% of active users receiving negative WOM in a step
TIPPING_POINT_PERSISTENCE = 5      # must hold for 5 consecutive steps

# ── 13. Scenario presets ────────────────────────────────────────────
#
# Each scenario provides:
#   patterns              – which dark patterns are active
#   dark_pattern_intensity – global intensity scalar  [0, 1]
#   adaptive_platform     – whether the platform adapts
#   customer_support_quality – base support quality   [0, 1]
#   reputation_range      – initial reputation (low, high)

SCENARIOS: dict[str, dict] = {
    "control": {
        "patterns": {
            "forced_trial": False,
            "hard_cancel": False,
            "drip_pricing": False,
        },
        "dark_pattern_intensity": 0.0,
        "adaptive_platform": False,
        "customer_support_quality": 0.50,
        "reputation_range": (70, 80),
    },
    "low_intensity": {
        "patterns": {
            "forced_trial": True,
            "hard_cancel": True,
            "drip_pricing": True,
        },
        "dark_pattern_intensity": 0.20,
        "adaptive_platform": False,
        "customer_support_quality": 0.40,
        "reputation_range": (60, 75),
    },
    "medium_intensity": {
        "patterns": {
            "forced_trial": True,
            "hard_cancel": True,
            "drip_pricing": True,
        },
        "dark_pattern_intensity": 0.50,
        "adaptive_platform": False,
        "customer_support_quality": 0.30,
        "reputation_range": (50, 70),
    },
    "high_intensity": {
        "patterns": {
            "forced_trial": True,
            "hard_cancel": True,
            "drip_pricing": True,
        },
        "dark_pattern_intensity": 0.80,
        "adaptive_platform": False,
        "customer_support_quality": 0.20,
        "reputation_range": (40, 60),
    },
    "forced_trial_only": {
        "patterns": {
            "forced_trial": True,
            "hard_cancel": False,
            "drip_pricing": False,
        },
        "dark_pattern_intensity": 0.50,
        "adaptive_platform": False,
        "customer_support_quality": 0.30,
        "reputation_range": (50, 70),
    },
    "hard_cancel_only": {
        "patterns": {
            "forced_trial": False,
            "hard_cancel": True,
            "drip_pricing": False,
        },
        "dark_pattern_intensity": 0.50,
        "adaptive_platform": False,
        "customer_support_quality": 0.30,
        "reputation_range": (50, 70),
    },
    "drip_pricing_only": {
        "patterns": {
            "forced_trial": False,
            "hard_cancel": False,
            "drip_pricing": True,
        },
        "dark_pattern_intensity": 0.50,
        "adaptive_platform": False,
        "customer_support_quality": 0.30,
        "reputation_range": (50, 70),
    },
    "mixed_exploitative": {
        "patterns": {
            "forced_trial": True,
            "hard_cancel": True,
            "drip_pricing": True,
        },
        "dark_pattern_intensity": 0.70,
        "adaptive_platform": False,
        "customer_support_quality": 0.15,
        "reputation_range": (40, 55),
    },
    "mixed_adaptive": {
        "patterns": {
            "forced_trial": True,
            "hard_cancel": True,
            "drip_pricing": True,
        },
        "dark_pattern_intensity": 0.50,
        "adaptive_platform": True,
        "customer_support_quality": 0.40,
        "reputation_range": (50, 70),
    },
    "clean_competitor": {
        "patterns": {
            "forced_trial": False,
            "hard_cancel": False,
            "drip_pricing": False,
        },
        "dark_pattern_intensity": 0.0,
        "adaptive_platform": True,
        "customer_support_quality": 0.70,
        "reputation_range": (75, 90),
    },
}

# ── 14. DEFAULTS dict (backward compat with FastAPI service) ────────

DEFAULTS: dict[str, object] = {
    "num_users": DEFAULT_NUM_AGENTS,
    "network_type": DEFAULT_NETWORK_TYPE,
    "avg_degree": DEFAULT_AVG_NODE_DEGREE,
    "rewire_prob": DEFAULT_REWIRING_PROB,
    "max_steps": DEFAULT_MAX_STEPS,
    "seed": 42,
    "dark_pattern_intensity": 0.40,
    "pattern_forced_trial": True,
    "pattern_hard_cancel": True,
    "pattern_drip_pricing": True,
    "customer_support_quality": 0.30,
    "adaptive_platform": False,
    "social_influence_strength": DEFAULT_SOCIAL_INFLUENCE_STRENGTH,
    "review_visibility": REVIEW_VISIBILITY,
}
