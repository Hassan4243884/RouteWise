"""
Unit tests for routing/services/scorer.py

Verifies that the four priority criteria are applied in the correct order.
"""
import pytest

from routing.services.risk import RiskLevel, RiskSummary
from routing.services.scorer import ScoredRoute, rank_routes, recommended_route_id


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def make_summary(
    severe=0.0,
    no_travel=0.0,
    high=0.0,
    moderate=0.0,
    low=0.0,
    avg=0.0,
    worst=RiskLevel.LOW,
) -> RiskSummary:
    return RiskSummary(
        low_miles=low,
        moderate_miles=moderate,
        high_miles=high,
        severe_miles=severe,
        no_travel_miles=no_travel,
        worst_risk=worst,
        avg_risk_score=avg,
    )


def make_route(
    route_id: str,
    severe=0.0,
    no_travel=0.0,
    high=0.0,
    avg=0.0,
    duration=180,
) -> ScoredRoute:
    return ScoredRoute(
        route_id=route_id,
        risk_summary=make_summary(severe=severe, no_travel=no_travel, high=high, avg=avg),
        duration_minutes=duration,
    )


# ──────────────────────────────────────────────────────────────────────────────
# Priority 1: Fewest critical miles (severe + no_travel)
# ──────────────────────────────────────────────────────────────────────────────
class TestPriority1CriticalMiles:
    def test_fewer_severe_miles_wins(self):
        a = make_route("a", severe=10.0, high=0.0, avg=3.0, duration=120)
        b = make_route("b", severe=5.0, high=50.0, avg=2.5, duration=200)
        ranked = rank_routes([a, b])
        assert ranked[0].route_id == "b"

    def test_no_travel_counts_as_critical(self):
        a = make_route("a", severe=0.0, no_travel=5.0)
        b = make_route("b", severe=3.0, no_travel=0.0)
        ranked = rank_routes([a, b])
        # Both have 5 vs 3 critical miles → b wins
        assert ranked[0].route_id == "b"

    def test_zero_critical_beats_any_critical(self):
        a = make_route("a", severe=0.0)
        b = make_route("b", severe=0.1)
        ranked = rank_routes([a, b])
        assert ranked[0].route_id == "a"


# ──────────────────────────────────────────────────────────────────────────────
# Priority 2: Fewest high miles (tiebreaker when critical is equal)
# ──────────────────────────────────────────────────────────────────────────────
class TestPriority2HighMiles:
    def test_fewer_high_miles_wins_on_tie(self):
        a = make_route("a", severe=0.0, high=20.0, avg=1.0, duration=100)
        b = make_route("b", severe=0.0, high=10.0, avg=2.0, duration=200)
        ranked = rank_routes([a, b])
        assert ranked[0].route_id == "b"


# ──────────────────────────────────────────────────────────────────────────────
# Priority 3: Lowest average risk score
# ──────────────────────────────────────────────────────────────────────────────
class TestPriority3AvgRisk:
    def test_lower_avg_risk_wins_on_tie(self):
        a = make_route("a", severe=0, high=0, avg=1.5, duration=100)
        b = make_route("b", severe=0, high=0, avg=0.8, duration=200)
        ranked = rank_routes([a, b])
        assert ranked[0].route_id == "b"


# ──────────────────────────────────────────────────────────────────────────────
# Priority 4: Shortest travel time
# ──────────────────────────────────────────────────────────────────────────────
class TestPriority4Duration:
    def test_shorter_time_wins_on_all_tie(self):
        a = make_route("a", severe=0, high=0, avg=0, duration=200)
        b = make_route("b", severe=0, high=0, avg=0, duration=150)
        ranked = rank_routes([a, b])
        assert ranked[0].route_id == "b"


# ──────────────────────────────────────────────────────────────────────────────
# Three-route ranking
# ──────────────────────────────────────────────────────────────────────────────
class TestThreeRouteRanking:
    def test_three_routes_ranked_correctly(self):
        a = make_route("a", severe=5.0, high=10.0, avg=2.0, duration=180)
        b = make_route("b", severe=0.0, high=20.0, avg=1.5, duration=200)
        c = make_route("c", severe=0.0, high=5.0, avg=0.5, duration=220)
        ranked = rank_routes([a, b, c])
        ids = [r.route_id for r in ranked]
        assert ids == ["c", "b", "a"]

    def test_ranks_assigned_1_2_3(self):
        routes = [
            make_route("a", severe=5.0),
            make_route("b", severe=2.0),
            make_route("c", severe=0.0),
        ]
        ranked = rank_routes(routes)
        assert ranked[0].rank == 1
        assert ranked[1].rank == 2
        assert ranked[2].rank == 3

    def test_recommended_is_rank_1(self):
        routes = [
            make_route("a", severe=5.0),
            make_route("b", severe=0.0),
        ]
        ranked = rank_routes(routes)
        assert recommended_route_id(ranked) == "b"


# ──────────────────────────────────────────────────────────────────────────────
# Edge cases
# ──────────────────────────────────────────────────────────────────────────────
class TestEdgeCases:
    def test_single_route(self):
        routes = [make_route("only")]
        ranked = rank_routes(routes)
        assert len(ranked) == 1
        assert ranked[0].rank == 1

    def test_empty_raises(self):
        with pytest.raises(ValueError):
            recommended_route_id([])
