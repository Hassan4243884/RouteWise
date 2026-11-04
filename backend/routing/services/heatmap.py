"""
Heatmap grid generation.

Builds a uniform lat/lng grid within the route corridor bounding box,
fetches 0–48 hr forecasts for each grid point in parallel, and returns
49 "frames" (one per hour) that the frontend slider cycles through.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

from .risk import compute_heatmap_intensity
from .weather import fetch_heatmap_weather

# Grid resolution in degrees (~17 miles at mid-latitudes)
_DEFAULT_RESOLUTION_DEG = 0.25

# Padding around route bounding box so the heatmap bleeds slightly past the routes
_BOUNDS_PADDING_DEG = 0.5


@dataclass
class HeatmapPoint:
    lat: float
    lng: float
    intensity: float    # 0.0 – 1.0


@dataclass
class HeatmapFrame:
    hour_offset: int
    points: list[HeatmapPoint]


def build_heatmap(
    bounds: dict[str, float],
    resolution_deg: float = _DEFAULT_RESOLUTION_DEG,
    num_hours: int = 49,
) -> list[HeatmapFrame]:
    """
    Build heatmap frames for the corridor defined by `bounds`.

    Parameters
    ----------
    bounds:
        Dict with keys north, south, east, west (degrees).
    resolution_deg:
        Grid spacing in degrees.  Smaller = more detail, more API calls.
    num_hours:
        Number of frames to generate (default 49 = hours 0–48).

    Returns
    -------
    List of HeatmapFrame, one per hour offset.
    """
    # Pad bounding box
    padded = {
        "north": bounds["north"] + _BOUNDS_PADDING_DEG,
        "south": bounds["south"] - _BOUNDS_PADDING_DEG,
        "east": bounds["east"] + _BOUNDS_PADDING_DEG,
        "west": bounds["west"] - _BOUNDS_PADDING_DEG,
    }

    grid_points = _build_grid(padded, resolution_deg)
    if not grid_points:
        return []

    # Fetch weather for all grid points (parallel, 0–48 hours)
    weather_matrix = fetch_heatmap_weather(grid_points, num_hours=num_hours)

    # Build one frame per hour
    frames: list[HeatmapFrame] = []
    for hour in range(num_hours):
        points: list[HeatmapPoint] = []
        for i, (lat, lng) in enumerate(grid_points):
            weather = weather_matrix[i][hour]
            intensity = compute_heatmap_intensity(weather)
            if intensity > 0.01:  # skip near-zero points to keep payload small
                points.append(HeatmapPoint(lat=lat, lng=lng, intensity=intensity))
        frames.append(HeatmapFrame(hour_offset=hour, points=points))

    return frames


def _build_grid(
    bounds: dict[str, float],
    resolution: float,
    max_points: int = 36,
) -> list[tuple[float, float]]:
    """Generate a uniform grid of (lat, lng) points within bounds, capped to prevent API rate limits."""
    south = bounds["south"]
    north = bounds["north"]
    west = bounds["west"]
    east = bounds["east"]

    if south >= north or west >= east:
        return []

    lat_span = north - south
    lng_span = east - west

    # If bounding box is large, dynamically widen resolution so points <= max_points
    est_points = (lat_span / max(0.01, resolution) + 1) * (lng_span / max(0.01, resolution) + 1)
    if est_points > max_points:
        steps = max(2, int(math.isqrt(max_points)))
        resolution_lat = max(resolution, lat_span / (steps - 1))
        resolution_lng = max(resolution, lng_span / (steps - 1))
    else:
        resolution_lat = resolution
        resolution_lng = resolution

    lats = _arange(south, north, resolution_lat)
    lngs = _arange(west, east, resolution_lng)

    return [(round(lat, 4), round(lng, 4)) for lat in lats for lng in lngs]


def _arange(start: float, stop: float, step: float) -> list[float]:
    """Float-safe range generator."""
    values = []
    current = start
    while current <= stop + 1e-9:
        values.append(current)
        current = round(current + step, 6)
    return values
