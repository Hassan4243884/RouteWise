"""
Unit tests for routing/services/checkpoint.py

Tests haversine accuracy, checkpoint sampling at all three intervals,
interpolation correctness, ETA pro-rating, and edge cases.
"""
import math
from datetime import datetime, timedelta, timezone

import pytest

from routing.services.checkpoint import (
    Checkpoint,
    bounding_box,
    haversine_miles,
    route_distance_miles,
    sample_checkpoints,
)


# ──────────────────────────────────────────────────────────────────────────────
# Haversine accuracy
# ──────────────────────────────────────────────────────────────────────────────
class TestHaversine:
    def test_same_point_is_zero(self):
        assert haversine_miles((41.85, -87.65), (41.85, -87.65)) == 0.0

    def test_chicago_to_indianapolis_approx(self):
        # Chicago (41.85, -87.65) to Indianapolis (39.77, -86.16)
        # As-the-crow-flies distance is ~163.5 miles (road distance is ~181 miles)
        d = haversine_miles((41.85, -87.65), (39.77, -86.16))
        assert 150 < d < 175

    def test_symmetry(self):
        p1, p2 = (40.0, -80.0), (41.0, -81.0)
        assert abs(haversine_miles(p1, p2) - haversine_miles(p2, p1)) < 0.001

    def test_one_degree_lat_approx_69_miles(self):
        # 1° latitude ≈ 69 miles
        d = haversine_miles((40.0, -80.0), (41.0, -80.0))
        assert 68 < d < 70


# ──────────────────────────────────────────────────────────────────────────────
# route_distance_miles
# ──────────────────────────────────────────────────────────────────────────────
class TestRouteDistanceMiles:
    def test_straight_north_south(self):
        poly = [(40.0, -80.0), (41.0, -80.0), (42.0, -80.0)]
        d = route_distance_miles(poly)
        assert abs(d - haversine_miles((40.0, -80.0), (42.0, -80.0))) < 0.5

    def test_single_point_is_zero(self):
        assert route_distance_miles([(40.0, -80.0)]) == 0.0


# ──────────────────────────────────────────────────────────────────────────────
# sample_checkpoints
# ──────────────────────────────────────────────────────────────────────────────
DEPARTURE = datetime(2026, 11, 4, 8, 0, 0, tzinfo=timezone.utc)


def make_polyline_approx_miles(n_degrees: float) -> list[tuple[float, float]]:
    """Generate a north-south polyline of approximately n_degrees × 69 miles."""
    # Each degree of latitude ≈ 69 miles
    step = n_degrees / 10
    return [(40.0 + i * step, -80.0) for i in range(11)]


class TestSampleCheckpoints:
    def test_empty_polyline_returns_no_checkpoints(self):
        cps = sample_checkpoints([], 25, 3600, DEPARTURE)
        assert cps == []

    def test_single_point_returns_no_checkpoints(self):
        cps = sample_checkpoints([(40.0, -80.0)], 25, 3600, DEPARTURE)
        assert cps == []

    def test_route_shorter_than_interval_returns_no_checkpoints(self):
        # 5-mile route, 25-mile interval → no checkpoint
        poly = [(40.0, -80.0), (40.07, -80.0)]   # ~4.8 miles
        cps = sample_checkpoints(poly, 25, 3600, DEPARTURE)
        assert cps == []

    def test_checkpoint_count_at_50_mile_interval(self):
        # ~200-mile route ≈ 200/50 = 4 checkpoints at miles 50, 100, 150, 200 (but not at end)
        poly = make_polyline_approx_miles(200 / 69)
        duration_s = 4 * 3600
        cps = sample_checkpoints(poly, 50, duration_s, DEPARTURE)
        assert len(cps) >= 2

    def test_checkpoint_count_at_25_mile_interval(self):
        poly = make_polyline_approx_miles(150 / 69)   # ~150 miles
        cps = sample_checkpoints(poly, 25, 5 * 3600, DEPARTURE)
        # Expect roughly 5 checkpoints (at 25, 50, 75, 100, 125 miles)
        assert len(cps) >= 4

    def test_checkpoint_count_at_10_mile_interval(self):
        poly = make_polyline_approx_miles(100 / 69)   # ~100 miles
        cps = sample_checkpoints(poly, 10, 2 * 3600, DEPARTURE)
        # Expect roughly 9 checkpoints (10, 20, … 90 miles)
        assert len(cps) >= 7

    def test_checkpoints_are_ordered_by_distance(self):
        poly = make_polyline_approx_miles(150 / 69)
        cps = sample_checkpoints(poly, 25, 5 * 3600, DEPARTURE)
        dists = [cp.distance_from_start_miles for cp in cps]
        assert dists == sorted(dists)

    def test_checkpoint_spacing_is_approximately_interval(self):
        poly = make_polyline_approx_miles(150 / 69)
        cps = sample_checkpoints(poly, 25, 5 * 3600, DEPARTURE)
        if len(cps) >= 2:
            for i in range(1, len(cps)):
                gap = cps[i].distance_from_start_miles - cps[i - 1].distance_from_start_miles
                assert abs(gap - 25) < 0.5  # within half a mile

    def test_eta_increases_with_distance(self):
        poly = make_polyline_approx_miles(150 / 69)
        cps = sample_checkpoints(poly, 25, 5 * 3600, DEPARTURE)
        for i in range(1, len(cps)):
            assert cps[i].eta > cps[i - 1].eta

    def test_eta_is_after_departure(self):
        poly = make_polyline_approx_miles(100 / 69)
        cps = sample_checkpoints(poly, 25, 3 * 3600, DEPARTURE)
        for cp in cps:
            assert cp.eta > DEPARTURE

    def test_indices_are_sequential(self):
        poly = make_polyline_approx_miles(100 / 69)
        cps = sample_checkpoints(poly, 25, 3 * 3600, DEPARTURE)
        for i, cp in enumerate(cps):
            assert cp.index == i

    def test_lat_lng_within_polyline_bounds(self):
        poly = make_polyline_approx_miles(100 / 69)
        cps = sample_checkpoints(poly, 25, 3 * 3600, DEPARTURE)
        min_lat = min(p[0] for p in poly)
        max_lat = max(p[0] for p in poly)
        for cp in cps:
            assert min_lat <= cp.lat <= max_lat


# ──────────────────────────────────────────────────────────────────────────────
# bounding_box
# ──────────────────────────────────────────────────────────────────────────────
class TestBoundingBox:
    def test_single_polyline(self):
        poly = [(40.0, -87.0), (41.0, -86.0), (39.5, -85.5)]
        bb = bounding_box([poly])
        assert bb["north"] == 41.0
        assert bb["south"] == 39.5
        assert bb["east"] == -85.5
        assert bb["west"] == -87.0

    def test_multiple_polylines(self):
        poly1 = [(40.0, -87.0), (41.0, -86.0)]
        poly2 = [(38.0, -85.0), (42.0, -84.0)]
        bb = bounding_box([poly1, poly2])
        assert bb["north"] == 42.0
        assert bb["south"] == 38.0
        assert bb["east"] == -84.0
        assert bb["west"] == -87.0
