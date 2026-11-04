"""
Open-Meteo weather fetching service.

Strategy:
- For route checkpoints: batch-fetch all unique locations in parallel using
  ThreadPoolExecutor so we make O(unique_points) requests concurrently, not
  O(checkpoints × routes) sequentially.
- For heatmap grid: same pattern across a uniform lat/lng grid.
- All requests are fire-and-forget with a short timeout; failures fall back
  to a "no weather data" placeholder so the route is still returned.

Open-Meteo API:
  https://api.open-meteo.com/v1/forecast
  Free, no API key, rate-limit-friendly.
"""
from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any

import httpx
from django.conf import settings

from .risk import WeatherData

logger = logging.getLogger(__name__)

_OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

# Fields we request from Open-Meteo hourly data
_HOURLY_VARS = "wind_speed_10m,rain,snowfall,temperature_2m,weather_code"

# Neutral fallback when weather fetch fails for a point
_FALLBACK_WEATHER = WeatherData(
    wind_speed_mph=0.0,
    rain_in_hr=0.0,
    snow_in_hr=0.0,
    temperature_f=55.0,
    weather_code=0,
)


import time

# Simple in-memory cache: (round_lat, round_lng) -> (cached_at, data)
_CACHE: dict[tuple[float, float], tuple[float, dict[str, Any]]] = {}
_CACHE_TTL = 900  # 15 minutes


# ──────────────────────────────────────────────────────────────────────────────
# Single-point fetch
# ──────────────────────────────────────────────────────────────────────────────
def _fetch_single(lat: float, lng: float) -> dict[str, Any] | None:
    """
    Fetch 3-day hourly forecast for one (lat, lng) from Open-Meteo.
    Uses an in-memory cache and backs off on HTTP 429.
    """
    cache_key = (round(lat, 2), round(lng, 2))
    now = time.time()
    if cache_key in _CACHE:
        cached_time, cached_data = _CACHE[cache_key]
        if now - cached_time < _CACHE_TTL:
            return cached_data

    params = {
        "latitude": round(lat, 4),
        "longitude": round(lng, 4),
        "hourly": _HOURLY_VARS,
        "wind_speed_unit": "mph",
        "precipitation_unit": "inch",
        "forecast_days": 3,
        "timezone": "auto",
    }
    timeout = getattr(settings, "HTTP_TIMEOUT", 15) if settings.configured else 15

    for attempt in range(2):
        try:
            resp = httpx.get(_OPEN_METEO_URL, params=params, timeout=timeout)
            if resp.status_code == 429:
                # Rate limited: wait briefly before retrying
                time.sleep(0.5 * (attempt + 1))
                continue
            resp.raise_for_status()
            data = resp.json()
            _CACHE[cache_key] = (now, data)
            return data
        except Exception as exc:
            if attempt == 0:
                time.sleep(0.3)
                continue
            logger.warning("Open-Meteo fetch failed for (%.4f, %.4f): %s", lat, lng, exc)
            return None
    return None


def _extract_at_hour(data: dict[str, Any], target_hour: int) -> WeatherData:
    """
    Pull the hourly forecast at index `target_hour` (0-based) from a
    single Open-Meteo response dict.

    Open-Meteo returns hourly arrays starting at hour 0 of the current day in
    the location's timezone.  We clamp to the last available index if target
    is beyond the array.
    """
    hourly = data.get("hourly", {})
    n = len(hourly.get("time", []))
    idx = min(target_hour, n - 1) if n > 0 else 0

    def get(key: str, default: float = 0.0) -> float:
        arr = hourly.get(key, [])
        if idx < len(arr) and arr[idx] is not None:
            return float(arr[idx])
        return default

    return WeatherData(
        wind_speed_mph=get("wind_speed_10m"),
        rain_in_hr=get("rain"),
        snow_in_hr=get("snowfall"),
        temperature_f=get("temperature_2m", 55.0),
        weather_code=int(get("weather_code", 0)),
    )


# ──────────────────────────────────────────────────────────────────────────────
# Batch fetch for checkpoints
# ──────────────────────────────────────────────────────────────────────────────
def fetch_checkpoint_weather(
    checkpoints: list[tuple[float, float, datetime]],
) -> list[WeatherData]:
    """
    Fetch weather for a list of (lat, lng, eta) checkpoint tuples in parallel.

    The Open-Meteo `hourly` array starts at hour 0 of the current UTC day.
    We map each checkpoint's ETA to the closest hour index.

    Returns a list of WeatherData with the same length as `checkpoints`.
    """
    if not checkpoints:
        return []

    # Deduplicate by rounded coordinate to reduce API calls
    unique_coords: dict[tuple[float, float], dict[str, Any] | None] = {}
    rounded_keys: list[tuple[float, float]] = []

    for lat, lng, _eta in checkpoints:
        key = (round(lat, 2), round(lng, 2))
        rounded_keys.append(key)
        if key not in unique_coords:
            unique_coords[key] = None  # placeholder

    # Parallel fetch
    with ThreadPoolExecutor(max_workers=5) as pool:
        future_to_key = {
            pool.submit(_fetch_single, lat, lng): (lat, lng)
            for lat, lng in unique_coords.keys()
        }
        for future in as_completed(future_to_key):
            key = future_to_key[future]
            unique_coords[key] = future.result()  # may be None if failed

    # Map results back to each checkpoint
    from datetime import timezone
    now_utc = datetime.now(timezone.utc)
    results: list[WeatherData] = []

    for (lat, lng, eta), coord_key in zip(checkpoints, rounded_keys):
        data = unique_coords.get(coord_key)
        if data is None:
            results.append(_FALLBACK_WEATHER)
            continue

        # Ensure eta is timezone-aware in UTC
        eta_utc = eta if eta.tzinfo is not None else eta.replace(tzinfo=timezone.utc)

        # Determine which hourly index corresponds to the ETA
        # Open-Meteo hourly[0] = start of the current day (hour 0)
        # We compute offset in hours from now (rounded down)
        hours_from_now = max(0, int((eta_utc - now_utc).total_seconds() / 3600))
        results.append(_extract_at_hour(data, hours_from_now))

    return results


# ──────────────────────────────────────────────────────────────────────────────
# Batch fetch for heatmap grid
# ──────────────────────────────────────────────────────────────────────────────
def fetch_heatmap_weather(
    grid_points: list[tuple[float, float]],
    num_hours: int = 49,
) -> list[list[WeatherData]]:
    """
    Fetch `num_hours` of hourly weather for each grid point.

    Returns a 2D list: result[point_idx][hour_offset] = WeatherData.

    All grid points are fetched in parallel.
    """
    if not grid_points:
        return []

    # Fetch all grid points in parallel
    raw_data: list[dict[str, Any] | None] = [None] * len(grid_points)

    with ThreadPoolExecutor(max_workers=5) as pool:
        future_to_idx = {
            pool.submit(_fetch_single, lat, lng): i
            for i, (lat, lng) in enumerate(grid_points)
        }
        for future in as_completed(future_to_idx):
            idx = future_to_idx[future]
            raw_data[idx] = future.result()

    # Extract per-hour WeatherData for each point
    result: list[list[WeatherData]] = []
    for data in raw_data:
        if data is None:
            result.append([_FALLBACK_WEATHER] * num_hours)
        else:
            hours = [_extract_at_hour(data, h) for h in range(num_hours)]
            result.append(hours)

    return result
