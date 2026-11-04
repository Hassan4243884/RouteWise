"""
Weather risk classification engine.

Implements the exact rules from the assessment:

Weather thresholds
──────────────────
           Low       Moderate    High      Severe    No Travel
Wind       <25 mph   25–34       35–44     45–54     ≥55 mph
Rain       <0.10     0.10–0.25   0.25–0.50 0.50–1.00 >1.00  in/hr
Snow       <0.5      0.5–1.0     1.0–2.0   2.0–3.0   >3.0   in/hr

Load rules (applied after base risk, wind speed drives the upgrades)
─────────────────────────────────────────────────────────────────────
• wind ≥ 55 mph                        → No Travel  (any load)
• wind 45–54 mph + load > 30,000 lb   → No Travel  (overrides Severe)
• wind 35–44 mph + load > 40,000 lb   → at least Severe

Route risk level = worst checkpoint risk across all checkpoints.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum


# ──────────────────────────────────────────────────────────────────────────────
# Risk levels
# ──────────────────────────────────────────────────────────────────────────────
class RiskLevel(IntEnum):
    LOW = 0
    MODERATE = 1
    HIGH = 2
    SEVERE = 3
    NO_TRAVEL = 4

    @property
    def label(self) -> str:
        return self.name.lower().replace("_", "_")  # "no_travel" keeps underscore

    @property
    def display(self) -> str:
        return self.name.replace("_", " ").title()  # "No Travel"


# ──────────────────────────────────────────────────────────────────────────────
# Threshold helpers
# ──────────────────────────────────────────────────────────────────────────────
def _classify_by_thresholds(value: float, thresholds: list[float]) -> RiskLevel:
    """
    Classify `value` against ascending boundary thresholds.

    thresholds = [low_max, moderate_max, high_max, severe_max]
    value < thresholds[0]  → LOW
    value < thresholds[1]  → MODERATE
    value < thresholds[2]  → HIGH
    value < thresholds[3]  → SEVERE
    else                   → NO_TRAVEL
    """
    for level, boundary in zip(RiskLevel, thresholds):
        if value < boundary:
            return level
    return RiskLevel.NO_TRAVEL


# Assessment thresholds (upper boundary of each level, exclusive)
_WIND_BOUNDARIES = [25.0, 35.0, 45.0, 55.0]   # mph
_RAIN_BOUNDARIES = [0.10, 0.25, 0.50, 1.00]   # in/hr
_SNOW_BOUNDARIES = [0.5, 1.0, 2.0, 3.0]       # in/hr


# ──────────────────────────────────────────────────────────────────────────────
# Weather data container
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class WeatherData:
    wind_speed_mph: float
    rain_in_hr: float
    snow_in_hr: float
    temperature_f: float
    weather_code: int


# ──────────────────────────────────────────────────────────────────────────────
# Core classification functions
# ──────────────────────────────────────────────────────────────────────────────
def classify_base_risk(weather: WeatherData) -> RiskLevel:
    """
    Classify weather risk ignoring load weight.
    Returns the highest risk across wind, rain, and snow independently.
    """
    wind_risk = _classify_by_thresholds(weather.wind_speed_mph, _WIND_BOUNDARIES)
    rain_risk = _classify_by_thresholds(weather.rain_in_hr, _RAIN_BOUNDARIES)
    snow_risk = _classify_by_thresholds(weather.snow_in_hr, _SNOW_BOUNDARIES)
    return max(wind_risk, rain_risk, snow_risk)


def apply_load_rules(base_risk: RiskLevel, wind_mph: float, load_lbs: float) -> RiskLevel:
    """
    Upgrade `base_risk` based on load weight and wind speed.

    Rules (in priority order):
    1. wind ≥ 55 → No Travel regardless of load.
    2. wind 45–54 + load > 30,000 → No Travel.
    3. wind 35–44 + load > 40,000 → at least Severe.
    """
    # Rule 1: absolute wind ceiling
    if wind_mph >= 55.0:
        return RiskLevel.NO_TRAVEL

    # Rule 2: high wind + heavy load
    if wind_mph >= 45.0 and load_lbs > 30_000:
        return RiskLevel.NO_TRAVEL

    # Rule 3: moderate-high wind + very heavy load
    if wind_mph >= 35.0 and load_lbs > 40_000:
        return max(base_risk, RiskLevel.SEVERE)

    return base_risk


def classify_checkpoint(weather: WeatherData, load_lbs: float) -> RiskLevel:
    """
    Full classification for a single checkpoint.
    Combines weather-based risk and load rules.
    """
    base = classify_base_risk(weather)
    return apply_load_rules(base, weather.wind_speed_mph, load_lbs)


# ──────────────────────────────────────────────────────────────────────────────
# Route-level aggregation
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class RiskSummary:
    """Aggregated risk statistics for one route."""
    low_miles: float
    moderate_miles: float
    high_miles: float
    severe_miles: float
    no_travel_miles: float
    worst_risk: RiskLevel
    avg_risk_score: float       # 0.0–4.0, used for tiebreaking

    @property
    def critical_miles(self) -> float:
        """Severe + No Travel miles (treated equally in primary sort key)."""
        return self.severe_miles + self.no_travel_miles


def compute_risk_summary(
    risk_levels: list[RiskLevel],
    segment_miles: list[float],
) -> RiskSummary:
    """
    Aggregate per-checkpoint risk levels into route-level statistics.

    Parameters
    ----------
    risk_levels:
        Risk level for each checkpoint.
    segment_miles:
        Miles "represented" by each checkpoint (distance to next checkpoint,
        or remaining miles for the last segment). Same length as risk_levels.
    """
    if not risk_levels:
        return RiskSummary(0, 0, 0, 0, 0, RiskLevel.LOW, 0.0)

    buckets: dict[RiskLevel, float] = {r: 0.0 for r in RiskLevel}
    for risk, miles in zip(risk_levels, segment_miles):
        buckets[risk] += miles

    worst = max(risk_levels)
    total_miles = sum(segment_miles) or 1.0
    avg_score = sum(r.value * m for r, m in zip(risk_levels, segment_miles)) / total_miles

    return RiskSummary(
        low_miles=round(buckets[RiskLevel.LOW], 2),
        moderate_miles=round(buckets[RiskLevel.MODERATE], 2),
        high_miles=round(buckets[RiskLevel.HIGH], 2),
        severe_miles=round(buckets[RiskLevel.SEVERE], 2),
        no_travel_miles=round(buckets[RiskLevel.NO_TRAVEL], 2),
        worst_risk=worst,
        avg_risk_score=round(avg_score, 4),
    )


def compute_heatmap_intensity(weather: WeatherData) -> float:
    """
    Convert weather conditions to a 0–1 intensity value for the heatmap layer.
    Uses the maximum normalized score across wind, rain, and snow.
    """
    wind_score = min(weather.wind_speed_mph / 55.0, 1.0)
    rain_score = min(weather.rain_in_hr / 1.0, 1.0)
    snow_score = min(weather.snow_in_hr / 3.0, 1.0)
    return round(max(wind_score, rain_score, snow_score), 4)
