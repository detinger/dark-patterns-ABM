"""Tests for app.simulation.patterns — DarkPattern, exposure, detection, harm."""

import random


def test_dark_pattern_from_config():
    from app.simulation.patterns import DarkPattern
    dp = DarkPattern.from_config("drip_pricing", intensity=0.5)
    assert dp.name == "drip_pricing"
    assert dp.intensity == 0.5
    assert dp.detectability > 0


def test_dark_pattern_from_config_all_patterns():
    from app.simulation.patterns import DarkPattern
    from app.simulation.config import DARK_PATTERN_DEFAULTS
    for name in DARK_PATTERN_DEFAULTS:
        dp = DarkPattern.from_config(name, intensity=0.3)
        assert dp.name == name


def test_calculate_exposure_zero_intensity():
    from app.simulation.patterns import calculate_exposure
    random.seed(42)
    exposures = sum(calculate_exposure(0.0) for _ in range(1000))
    assert exposures < 100


def test_calculate_exposure_full_intensity():
    from app.simulation.patterns import calculate_exposure
    random.seed(42)
    exposures = sum(calculate_exposure(1.0) for _ in range(1000))
    assert exposures > 900


def test_calculate_detection_high_literacy():
    from app.simulation.patterns import calculate_detection
    random.seed(42)
    detections = sum(calculate_detection(0.9, 0.8, 0.0) for _ in range(1000))
    assert detections > 500


def test_calculate_detection_low_literacy():
    from app.simulation.patterns import calculate_detection
    random.seed(42)
    detections = sum(calculate_detection(0.2, 0.25, 0.0) for _ in range(1000))
    assert detections < 200


def test_calculate_detection_warning_awareness_boosts():
    from app.simulation.patterns import calculate_detection
    random.seed(42)
    without = sum(calculate_detection(0.5, 0.5, 0.0) for _ in range(2000))
    random.seed(42)
    with_aw = sum(calculate_detection(0.5, 0.5, 0.8) for _ in range(2000))
    assert with_aw > without


def test_calculate_detection_capped():
    from app.simulation.patterns import calculate_detection, MAX_DETECTION_PROBABILITY
    random.seed(42)
    detections = sum(calculate_detection(1.0, 1.0, 1.0) for _ in range(10000))
    assert detections / 10000 <= MAX_DETECTION_PROBABILITY + 0.02


def test_calculate_harm_detected_greater_than_hidden():
    from app.simulation.patterns import DarkPattern, calculate_harm
    dp = DarkPattern.from_config("drip_pricing", intensity=0.5)
    detected_harm = calculate_harm(dp, 0.5, True, 1.0)
    hidden_harm = calculate_harm(dp, 0.5, False, 1.0)
    assert detected_harm > hidden_harm


def test_calculate_harm_zero_intensity():
    from app.simulation.patterns import DarkPattern, calculate_harm
    dp = DarkPattern.from_config("forced_trial", intensity=0.0)
    assert calculate_harm(dp, 0.0, True, 1.0) == 0.0
