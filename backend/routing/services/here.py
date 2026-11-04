"""
HERE Routing API client.

Responsibilities:
- Geocode a place name or address to (lat, lng).
- Fetch 3 truck route alternatives and return decoded polylines + metadata.
- Decode HERE Flexible Polyline format internally (no extra dependency needed).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

import httpx
from django.conf import settings

logger = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# HERE Flexible Polyline decoder
# ──────────────────────────────────────────────────────────────────────────────
_ENCODING_TABLE = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_"
_DECODING_TABLE: list[int | None] = [None] * 128
for _i, _c in enumerate(_ENCODING_TABLE):
    _DECODING_TABLE[ord(_c)] = _i


def _decode_unsigned(encoded: str, idx: int) -> tuple[int, int]:
    """Decode a single variable-length unsigned integer starting at idx.
    Returns (decoded_value, new_idx).
    """
    result = 0
    shift = 0
    while True:
        c = _DECODING_TABLE[ord(encoded[idx])]
        if c is None:
            raise ValueError(f"Invalid character in flexible polyline at index {idx}")
        idx += 1
        result |= (c & 0x1F) << shift
        shift += 5
        if c < 0x20:
            break
    return result, idx


def decode_flexible_polyline(encoded: str) -> list[tuple[float, float]]:
    """Decode a HERE Flexible Polyline encoded string into a list of (lat, lng) tuples."""
    if not encoded:
        return []

    header_val, idx = _decode_unsigned(encoded, 0)
    # Bits 0-3: precision; bits 4-6: 3rd dim type (we ignore); bits 7-9: 3rd dim precision
    precision = header_val & 0x0F
    factor = 10 ** precision

    # Check if 3D dimension present (we skip the 3rd value if so)
    third_dim_bits = (header_val >> 4) & 0x07
    has_third_dim = third_dim_bits != 0

    coords: list[tuple[float, float]] = []
    last_lat = 0
    last_lng = 0

    while idx < len(encoded):
        # Latitude delta
        raw, idx = _decode_unsigned(encoded, idx)
        delta_lat = (~(raw >> 1) if (raw & 1) else (raw >> 1))
        last_lat += delta_lat

        # Longitude delta
        raw, idx = _decode_unsigned(encoded, idx)
        delta_lng = (~(raw >> 1) if (raw & 1) else (raw >> 1))
        last_lng += delta_lng

        # Skip 3rd dimension if present (altitude/elevation)
        if has_third_dim and idx < len(encoded):
            _, idx = _decode_unsigned(encoded, idx)

        coords.append((last_lat / factor, last_lng / factor))

    return coords


# ──────────────────────────────────────────────────────────────────────────────
from .openrouteservice import ORSError, ORSRoute

# ──────────────────────────────────────────────────────────────────────────────
# Data structures
# ──────────────────────────────────────────────────────────────────────────────
HereRoute = ORSRoute
HereAPIError = ORSError


# ──────────────────────────────────────────────────────────────────────────────
# Geocoding
# ──────────────────────────────────────────────────────────────────────────────
def geocode(place: str) -> tuple[float, float]:
    """
    Convert a place name or address to (lat, lng) using HERE Geocoding API.

    Raises:
        HereAPIError: if the place cannot be geocoded or HERE returns an error.
    """
    api_key = getattr(settings, "HERE_API_KEY", "") if settings.configured else ""
    if not api_key:
        raise HereAPIError("HERE_API_KEY is not configured in environment")

    timeout = getattr(settings, "HTTP_TIMEOUT", 15) if settings.configured else 15
    url = "https://geocode.search.hereapi.com/v1/geocode"
    params = {"q": place, "apiKey": api_key}

    try:
        resp = httpx.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
    except httpx.TimeoutException:
        raise HereAPIError(f"Geocoding request timed out for '{place}'")
    except httpx.HTTPStatusError as e:
        raise HereAPIError(f"HERE Geocoding API error {e.response.status_code}: {e.response.text[:200]}")

    data = resp.json()
    items = data.get("items", [])
    if not items:
        raise HereAPIError(f"No geocoding results found for '{place}'")

    pos = items[0]["position"]
    logger.debug("Geocoded '%s' → lat=%.5f lng=%.5f", place, pos["lat"], pos["lng"])
    return pos["lat"], pos["lng"]


# ──────────────────────────────────────────────────────────────────────────────
# Route fetching
# ──────────────────────────────────────────────────────────────────────────────
_ROUTE_LABELS = ["Route A", "Route B", "Route C"]


def fetch_routes(
    origin_lat: float,
    origin_lng: float,
    dest_lat: float,
    dest_lng: float,
) -> list[HereRoute]:
    """
    Fetch up to 3 truck route alternatives from HERE Routing API v8.

    Returns a list of HereRoute objects (1–3 items).

    Raises:
        HereAPIError: on API errors or if no routes are returned.
    """
    api_key = getattr(settings, "HERE_API_KEY", "") if settings.configured else ""
    if not api_key:
        raise HereAPIError("HERE_API_KEY is not configured in environment")

    timeout = getattr(settings, "HTTP_TIMEOUT", 15) if settings.configured else 15
    url = "https://router.hereapi.com/v8/routes"
    params = {
        "transportMode": "truck",
        "origin": f"{origin_lat},{origin_lng}",
        "destination": f"{dest_lat},{dest_lng}",
        "return": "polyline,summary",
        "alternatives": 2,          # request 2 alternatives → up to 3 routes total
        "apikey": api_key,
    }

    try:
        resp = httpx.get(url, params=params, timeout=timeout)
        resp.raise_for_status()
    except httpx.TimeoutException:
        raise HereAPIError("HERE Routing API request timed out")
    except httpx.HTTPStatusError as e:
        raise HereAPIError(
            f"HERE Routing API error {e.response.status_code}: {e.response.text[:200]}"
        )

    data = resp.json()
    raw_routes = data.get("routes", [])
    if not raw_routes:
        raise HereAPIError("HERE returned no routes for the given origin/destination")

    routes: list[HereRoute] = []
    for idx, raw in enumerate(raw_routes[:3]):
        route_id = f"route_{idx}"
        label = _ROUTE_LABELS[idx]

        # Aggregate across sections (direct routes typically have one section)
        full_polyline: list[tuple[float, float]] = []
        total_distance = 0
        total_duration = 0

        for section in raw.get("sections", []):
            encoded = section.get("polyline", "")
            if encoded:
                section_coords = decode_flexible_polyline(encoded)
                # Avoid duplicating the join point between sections
                if full_polyline and section_coords:
                    section_coords = section_coords[1:]
                full_polyline.extend(section_coords)

            summary = section.get("summary", {})
            total_distance += summary.get("length", 0)      # meters
            total_duration += summary.get("duration", 0)    # seconds

        if not full_polyline:
            logger.warning("Route %s has no decodable polyline — skipping", route_id)
            continue

        routes.append(
            HereRoute(
                id=route_id,
                label=label,
                polyline=full_polyline,
                distance_meters=total_distance,
                duration_seconds=total_duration,
            )
        )
        logger.debug(
            "Route %s: %d points, %.1f km, %d min",
            route_id,
            len(full_polyline),
            total_distance / 1000,
            total_duration // 60,
        )

    if not routes:
        raise HereAPIError("All HERE route alternatives had empty polylines")

    return routes
