"""
Route scoring and ranking.

Priority order (lower = better, lexicographic):
  1. Fewest Severe + No Travel miles  (critical_miles)
  2. Fewest High miles
  3. Lowest average risk score (float 0.0–4.0)
  4. Shortest travel time (minutes)

The first route in the returned list is the recommended route.
"""
from __future__ import annotations

from dataclasses import dataclass

from .risk import RiskLevel, RiskSummary


@dataclass
class ScoredRoute:
    """Associates a route ID with its scoring inputs."""
    route_id: str
    risk_summary: RiskSummary
    duration_minutes: int
    rank: int = 0          # filled in after sorting (1 = best)


def rank_routes(routes: list[ScoredRoute]) -> list[ScoredRoute]:
    """
    Sort routes by the assessment's priority order and assign `rank`.
    Returns the list sorted best → worst.
    """
    def sort_key(r: ScoredRoute) -> tuple:
        return (
            r.risk_summary.critical_miles,     # severe + no_travel (primary)
            r.risk_summary.high_miles,          # high miles (secondary)
            r.risk_summary.avg_risk_score,      # average risk (tertiary)
            r.duration_minutes,                 # travel time (quaternary)
        )

    sorted_routes = sorted(routes, key=sort_key)
    for i, route in enumerate(sorted_routes):
        route.rank = i + 1

    return sorted_routes


def recommended_route_id(ranked_routes: list[ScoredRoute]) -> str:
    """Return the ID of the best (rank=1) route."""
    if not ranked_routes:
        raise ValueError("Cannot recommend from empty route list")
    return ranked_routes[0].route_id
