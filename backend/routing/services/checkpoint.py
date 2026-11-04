"""
Checkpoint sampling along a route polyline.

Algorithm:
- Walk the decoded polyline accumulating Haversine distance.
- Every time the accumulated distance crosses a multiple of `interval_miles`,
  emit a checkpoint with:
  - Linearly interpolated (lat, lng)
  - Distance from start
  - Pro-rated ETA = departure + (distance_fraction × total_duration)
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta

# ──────────────────────────────────────────────────────────────────────────────
# Haversine distance
# ──────────────────────────────────────────────────────────────────────────────
_EARTH_RADIUS_MILES = 3_958.8


def haversine_miles(p1: tuple[float, float], p2: tuple[float, float]) -> float:
    """Return great-circle distance in miles between two (lat, lng) points."""
    lat1, lng1 = math.radians(p1[0]), math.radians(p1[1])
    lat2, lng2 = math.radians(p2[0]), math.radians(p2[1])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    a = math.sin(dlat / 2) ** 2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlng / 2) ** 2
    return 2 * _EARTH_RADIUS_MILES * math.asin(math.sqrt(a))


# ──────────────────────────────────────────────────────────────────────────────
# Data structure
# ──────────────────────────────────────────────────────────────────────────────
@dataclass
class Checkpoint:
    index: int
    lat: float
    lng: float
    distance_from_start_miles: float
    eta: datetime


# ──────────────────────────────────────────────────────────────────────────────
# Public API
# ──────────────────────────────────────────────────────────────────────────────
def sample_checkpoints(
    polyline: list[tuple[float, float]],
    interval_miles: float,
    total_duration_seconds: int,
    departure_time: datetime,
) -> list[Checkpoint]:
    """
    Walk `polyline` and emit a Checkpoint every `interval_miles`.

    Parameters
    ----------
    polyline:
        Ordered list of (lat, lng) from the routing API.
    interval_miles:
        Desired spacing between checkpoints (10, 25, or 50 miles).
    total_duration_seconds:
        Route total driving time used to pro-rate ETAs.
    departure_time:
        Departure datetime used as the ETA baseline.

    Returns
    -------
    List of Checkpoint objects.  May be empty for very short routes.
    """
    if len(polyline) < 2:
        return []

    # Compute total route length so we can pro-rate ETAs
    total_route_miles = _total_distance(polyline)
    if total_route_miles == 0:
        return []

    checkpoints: list[Checkpoint] = []
    accumulated_miles = 0.0
    next_threshold = interval_miles
    checkpoint_idx = 0

    prev_point = polyline[0]

    for point in polyline[1:]:
        seg_miles = haversine_miles(prev_point, point)

        # A single segment may cross multiple thresholds (long segments at low interval)
        while accumulated_miles + seg_miles >= next_threshold:
            # How far into this segment does the threshold fall?
            overshoot = (next_threshold - accumulated_miles)
            ratio = overshoot / seg_miles if seg_miles > 0 else 0.0

            # Linearly interpolate position
            lat = prev_point[0] + ratio * (point[0] - prev_point[0])
            lng = prev_point[1] + ratio * (point[1] - prev_point[1])

            # Pro-rate ETA by distance fraction
            fraction = next_threshold / total_route_miles
            eta = departure_time + timedelta(seconds=total_duration_seconds * fraction)

            checkpoints.append(
                Checkpoint(
                    index=checkpoint_idx,
                    lat=round(lat, 6),
                    lng=round(lng, 6),
                    distance_from_start_miles=round(next_threshold, 2),
                    eta=eta,
                )
            )
            checkpoint_idx += 1
            next_threshold += interval_miles

            # Stop if we've passed the end of the route
            if next_threshold > total_route_miles:
                break

        accumulated_miles += seg_miles
        prev_point = point

    return checkpoints


def _total_distance(polyline: list[tuple[float, float]]) -> float:
    """Sum of all segment distances in miles."""
    total = 0.0
    for i in range(len(polyline) - 1):
        total += haversine_miles(polyline[i], polyline[i + 1])
    return total


def route_distance_miles(polyline: list[tuple[float, float]]) -> float:
    """Public helper — total polyline length in miles."""
    return _total_distance(polyline)


def bounding_box(
    polylines: list[list[tuple[float, float]]],
) -> dict[str, float]:
    """
    Compute the bounding box (north/south/east/west) of one or more polylines.
    Used by the heatmap service.
    """
    all_lats = [lat for poly in polylines for lat, _ in poly]
    all_lngs = [lng for poly in polylines for _, lng in poly]
    return {
        "north": max(all_lats),
        "south": min(all_lats),
        "east": max(all_lngs),
        "west": min(all_lngs),
    }
