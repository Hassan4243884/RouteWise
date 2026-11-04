"""
Unit tests for routing/services/risk.py

Tests every boundary condition for wind, rain, and snow thresholds,
all three load rules, and the route-level RiskSummary aggregation.
"""
import pytest

from routing.services.risk import (
    RiskLevel,
    RiskSummary,
    WeatherData,
    apply_load_rules,
    classify_base_risk,
    classify_checkpoint,
    compute_risk_summary,
    compute_heatmap_intensity,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def weather(wind=0.0, rain=0.0, snow=0.0) -> WeatherData:
    return WeatherData(
        wind_speed_mph=wind,
        rain_in_hr=rain,
        snow_in_hr=snow,
        temperature_f=55.0,
        weather_code=0,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Wind threshold tests
# ──────────────────────────────────────────────────────────────────────────────
class TestWindThresholds:
    def test_wind_low(self):
        assert classify_base_risk(weather(wind=0.0)) == RiskLevel.LOW
        assert classify_base_risk(weather(wind=24.9)) == RiskLevel.LOW

    def test_wind_moderate_lower(self):
        assert classify_base_risk(weather(wind=25.0)) == RiskLevel.MODERATE

    def test_wind_moderate_upper(self):
        assert classify_base_risk(weather(wind=34.9)) == RiskLevel.MODERATE

    def test_wind_high_lower(self):
        assert classify_base_risk(weather(wind=35.0)) == RiskLevel.HIGH

    def test_wind_high_upper(self):
        assert classify_base_risk(weather(wind=44.9)) == RiskLevel.HIGH

    def test_wind_severe_lower(self):
        assert classify_base_risk(weather(wind=45.0)) == RiskLevel.SEVERE

    def test_wind_severe_upper(self):
        assert classify_base_risk(weather(wind=54.9)) == RiskLevel.SEVERE

    def test_wind_no_travel_boundary(self):
        assert classify_base_risk(weather(wind=55.0)) == RiskLevel.NO_TRAVEL

    def test_wind_no_travel_extreme(self):
        assert classify_base_risk(weather(wind=100.0)) == RiskLevel.NO_TRAVEL


# ──────────────────────────────────────────────────────────────────────────────
# Rain threshold tests
# ──────────────────────────────────────────────────────────────────────────────
class TestRainThresholds:
    def test_rain_low(self):
        assert classify_base_risk(weather(rain=0.0)) == RiskLevel.LOW
        assert classify_base_risk(weather(rain=0.099)) == RiskLevel.LOW

    def test_rain_moderate(self):
        assert classify_base_risk(weather(rain=0.10)) == RiskLevel.MODERATE
        assert classify_base_risk(weather(rain=0.249)) == RiskLevel.MODERATE

    def test_rain_high(self):
        assert classify_base_risk(weather(rain=0.25)) == RiskLevel.HIGH
        assert classify_base_risk(weather(rain=0.499)) == RiskLevel.HIGH

    def test_rain_severe(self):
        assert classify_base_risk(weather(rain=0.50)) == RiskLevel.SEVERE
        assert classify_base_risk(weather(rain=0.999)) == RiskLevel.SEVERE

    def test_rain_no_travel(self):
        assert classify_base_risk(weather(rain=1.00)) == RiskLevel.NO_TRAVEL
        assert classify_base_risk(weather(rain=5.0)) == RiskLevel.NO_TRAVEL


# ──────────────────────────────────────────────────────────────────────────────
# Snow threshold tests
# ──────────────────────────────────────────────────────────────────────────────
class TestSnowThresholds:
    def test_snow_low(self):
        assert classify_base_risk(weather(snow=0.0)) == RiskLevel.LOW
        assert classify_base_risk(weather(snow=0.49)) == RiskLevel.LOW

    def test_snow_moderate(self):
        assert classify_base_risk(weather(snow=0.5)) == RiskLevel.MODERATE
        assert classify_base_risk(weather(snow=0.99)) == RiskLevel.MODERATE

    def test_snow_high(self):
        assert classify_base_risk(weather(snow=1.0)) == RiskLevel.HIGH
        assert classify_base_risk(weather(snow=1.99)) == RiskLevel.HIGH

    def test_snow_severe(self):
        assert classify_base_risk(weather(snow=2.0)) == RiskLevel.SEVERE
        assert classify_base_risk(weather(snow=2.99)) == RiskLevel.SEVERE

    def test_snow_no_travel(self):
        assert classify_base_risk(weather(snow=3.0)) == RiskLevel.NO_TRAVEL
        assert classify_base_risk(weather(snow=10.0)) == RiskLevel.NO_TRAVEL


# ──────────────────────────────────────────────────────────────────────────────
# Max across conditions
# ──────────────────────────────────────────────────────────────────────────────
class TestMaxCondition:
    def test_rain_dominates(self):
        # wind=LOW, rain=HIGH, snow=LOW → HIGH
        assert classify_base_risk(weather(wind=10, rain=0.30, snow=0.1)) == RiskLevel.HIGH

    def test_snow_dominates(self):
        # wind=LOW, rain=LOW, snow=SEVERE → SEVERE
        assert classify_base_risk(weather(wind=5, rain=0.05, snow=2.5)) == RiskLevel.SEVERE

    def test_wind_dominates(self):
        # wind=NO_TRAVEL, rain=LOW, snow=LOW → NO_TRAVEL
        assert classify_base_risk(weather(wind=60, rain=0.0, snow=0.0)) == RiskLevel.NO_TRAVEL


# ──────────────────────────────────────────────────────────────────────────────
# Load rule tests
# ──────────────────────────────────────────────────────────────────────────────
class TestLoadRules:
    def test_rule1_wind_55_any_load(self):
        """wind ≥ 55 → No Travel regardless of load"""
        result = apply_load_rules(RiskLevel.NO_TRAVEL, wind_mph=55.0, load_lbs=1_000)
        assert result == RiskLevel.NO_TRAVEL

    def test_rule1_wind_55_light_load(self):
        """Even a very light load triggers No Travel at ≥ 55 mph"""
        result = apply_load_rules(RiskLevel.SEVERE, wind_mph=55.0, load_lbs=500)
        assert result == RiskLevel.NO_TRAVEL

    def test_rule1_wind_80_any_load(self):
        result = apply_load_rules(RiskLevel.LOW, wind_mph=80.0, load_lbs=0)
        assert result == RiskLevel.NO_TRAVEL

    def test_rule2_wind_45_54_heavy_load(self):
        """wind 45–54 + load > 30,000 → No Travel"""
        result = apply_load_rules(RiskLevel.SEVERE, wind_mph=48.0, load_lbs=30_001)
        assert result == RiskLevel.NO_TRAVEL

    def test_rule2_wind_45_54_light_load_not_upgraded(self):
        """wind 45–54 + load ≤ 30,000 → stays SEVERE (no upgrade to No Travel)"""
        result = apply_load_rules(RiskLevel.SEVERE, wind_mph=50.0, load_lbs=30_000)
        assert result == RiskLevel.SEVERE

    def test_rule2_wind_45_exact_boundary(self):
        result = apply_load_rules(RiskLevel.SEVERE, wind_mph=45.0, load_lbs=30_001)
        assert result == RiskLevel.NO_TRAVEL

    def test_rule3_wind_35_44_very_heavy_load(self):
        """wind 35–44 + load > 40,000 → at least Severe"""
        result = apply_load_rules(RiskLevel.HIGH, wind_mph=38.0, load_lbs=40_001)
        assert result == RiskLevel.SEVERE

    def test_rule3_does_not_downgrade(self):
        """Rule 3 only upgrades, never downgrades"""
        result = apply_load_rules(RiskLevel.NO_TRAVEL, wind_mph=38.0, load_lbs=45_000)
        assert result == RiskLevel.NO_TRAVEL

    def test_rule3_wind_35_exact_boundary(self):
        result = apply_load_rules(RiskLevel.HIGH, wind_mph=35.0, load_lbs=40_001)
        assert result == RiskLevel.SEVERE

    def test_rule3_load_at_boundary_no_upgrade(self):
        """load = exactly 40,000 lb → rule 3 does NOT apply"""
        result = apply_load_rules(RiskLevel.HIGH, wind_mph=38.0, load_lbs=40_000)
        assert result == RiskLevel.HIGH

    def test_no_load_rules_for_low_wind(self):
        """wind < 35 → load rules do not apply"""
        result = apply_load_rules(RiskLevel.LOW, wind_mph=20.0, load_lbs=80_000)
        assert result == RiskLevel.LOW


# ──────────────────────────────────────────────────────────────────────────────
# Full checkpoint classification
# ──────────────────────────────────────────────────────────────────────────────
class TestClassifyCheckpoint:
    def test_clear_weather_light_load(self):
        w = weather(wind=10, rain=0.0, snow=0.0)
        assert classify_checkpoint(w, load_lbs=10_000) == RiskLevel.LOW

    def test_severe_wind_heavy_load_becomes_no_travel(self):
        w = weather(wind=48.0)
        assert classify_checkpoint(w, load_lbs=35_000) == RiskLevel.NO_TRAVEL

    def test_moderate_wind_very_heavy_load_becomes_severe(self):
        w = weather(wind=40.0)
        assert classify_checkpoint(w, load_lbs=45_000) == RiskLevel.SEVERE


# ──────────────────────────────────────────────────────────────────────────────
# RiskSummary aggregation
# ──────────────────────────────────────────────────────────────────────────────
class TestComputeRiskSummary:
    def test_empty_checkpoints(self):
        summary = compute_risk_summary([], [])
        assert summary.worst_risk == RiskLevel.LOW
        assert summary.avg_risk_score == 0.0

    def test_all_low(self):
        risks = [RiskLevel.LOW] * 3
        miles = [25.0, 25.0, 25.0]
        summary = compute_risk_summary(risks, miles)
        assert summary.low_miles == 75.0
        assert summary.worst_risk == RiskLevel.LOW
        assert summary.avg_risk_score == 0.0

    def test_mixed_risk_worst_is_severe(self):
        risks = [RiskLevel.LOW, RiskLevel.HIGH, RiskLevel.SEVERE]
        miles = [50.0, 25.0, 25.0]
        summary = compute_risk_summary(risks, miles)
        assert summary.worst_risk == RiskLevel.SEVERE
        assert summary.high_miles == 25.0
        assert summary.severe_miles == 25.0
        # avg = (0*50 + 2*25 + 3*25) / 100 = 125/100 = 1.25
        assert abs(summary.avg_risk_score - 1.25) < 0.01

    def test_critical_miles_includes_no_travel(self):
        risks = [RiskLevel.SEVERE, RiskLevel.NO_TRAVEL]
        miles = [10.0, 5.0]
        summary = compute_risk_summary(risks, miles)
        assert summary.critical_miles == 15.0


# ──────────────────────────────────────────────────────────────────────────────
# Heatmap intensity
# ──────────────────────────────────────────────────────────────────────────────
class TestHeatmapIntensity:
    def test_calm_conditions(self):
        assert compute_heatmap_intensity(weather(0, 0, 0)) == 0.0

    def test_max_wind(self):
        assert compute_heatmap_intensity(weather(wind=55)) == 1.0

    def test_max_rain(self):
        assert compute_heatmap_intensity(weather(rain=1.0)) == 1.0

    def test_max_snow(self):
        assert compute_heatmap_intensity(weather(snow=3.0)) == 1.0

    def test_wind_partial(self):
        # 27.5 mph / 55 = 0.5
        result = compute_heatmap_intensity(weather(wind=27.5))
        assert abs(result - 0.5) < 0.01

    def test_intensity_clamped_at_1(self):
        assert compute_heatmap_intensity(weather(wind=200)) == 1.0
