"""
API views: RouteView and HeatmapView.

RouteView orchestrates the full pipeline:
  geocode → fetch HERE routes → sample checkpoints →
  fetch weather → classify risk → score routes → return JSON

HeatmapView builds a weather intensity grid for the forecast slider.
"""
from __future__ import annotations

import logging

from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView, exception_handler

from .serializers import HeatmapInputSerializer, RouteInputSerializer
from .services.checkpoint import (
    Checkpoint,
    bounding_box,
    route_distance_miles,
    sample_checkpoints,
)
from .services.heatmap import build_heatmap
from .services.openrouteservice import ORSError, ORSError as HereAPIError, fetch_routes, geocode
from .services.risk import (
    RiskLevel,
    RiskSummary,
    WeatherData,
    classify_checkpoint,
    compute_risk_summary,
)
from .services.scorer import ScoredRoute, rank_routes, recommended_route_id
from .services.weather import fetch_checkpoint_weather

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────────
# Custom exception handler — consistent error envelope
# ──────────────────────────────────────────────────────────────────────────────
def custom_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        # Wrap DRF's default response in our error envelope
        if not isinstance(response.data, dict) or "error" not in response.data:
            response.data = {"error": response.data}
    return response


class ServiceUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "An upstream service is temporarily unavailable."
    default_code = "service_unavailable"


class UnprocessableEntity(APIException):
    status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    default_detail = "The request could not be processed."
    default_code = "unprocessable_entity"


# ──────────────────────────────────────────────────────────────────────────────
# Response serialization helpers
# ──────────────────────────────────────────────────────────────────────────────
def _serialize_weather(w: WeatherData) -> dict:
    return {
        "wind_speed_mph": round(w.wind_speed_mph, 1),
        "rain_in_hr": round(w.rain_in_hr, 3),
        "snow_in_hr": round(w.snow_in_hr, 3),
        "temperature_f": round(w.temperature_f, 1),
        "weather_code": w.weather_code,
    }


def _serialize_checkpoint(cp: Checkpoint, weather: WeatherData, risk: RiskLevel) -> dict:
    return {
        "index": cp.index,
        "lat": cp.lat,
        "lng": cp.lng,
        "distance_from_start_miles": cp.distance_from_start_miles,
        "eta": cp.eta.isoformat(),
        "weather": _serialize_weather(weather),
        "risk_level": risk.name.lower(),
    }


def _serialize_summary(
    summary: RiskSummary,
    distance_miles: float,
    duration_minutes: int,
    rank: int,
) -> dict:
    return {
        "distance_miles": round(distance_miles, 1),
        "duration_minutes": duration_minutes,
        "low_miles": summary.low_miles,
        "moderate_miles": summary.moderate_miles,
        "high_miles": summary.high_miles,
        "severe_miles": summary.severe_miles,
        "no_travel_miles": summary.no_travel_miles,
        "worst_risk": summary.worst_risk.name.lower(),
        "avg_risk_score": summary.avg_risk_score,
        "rank": rank,
    }


# ──────────────────────────────────────────────────────────────────────────────
# RouteView
# ──────────────────────────────────────────────────────────────────────────────
class RouteView(APIView):
    """
    POST /api/routes/

    Pipeline:
    1. Validate input
    2. Geocode origin + destination
    3. Fetch 3 HERE truck routes
    4. For each route: sample checkpoints, fetch weather, classify risk
    5. Score + rank routes
    6. Return JSON
    """

    def post(self, request: Request) -> Response:
        serializer = RouteInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        origin: str = data["origin"]
        destination: str = data["destination"]
        departure_time = data["departure_time"]
        load_lbs: float = data["load_weight_lbs"]
        interval_miles: int = data["checkpoint_interval_miles"]

        # ── Step 1: Geocode ────────────────────────────────────────────────
        try:
            origin_lat, origin_lng = geocode(origin)
            dest_lat, dest_lng = geocode(destination)
        except HereAPIError as exc:
            logger.error("Geocoding failed: %s", exc)
            return Response(
                {"error": str(exc), "code": "GEOCODING_FAILED"},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        # ── Step 2: Fetch routes ───────────────────────────────────────────
        try:
            here_routes = fetch_routes(origin_lat, origin_lng, dest_lat, dest_lng)
        except HereAPIError as exc:
            logger.error("HERE routing failed: %s", exc)
            return Response(
                {"error": str(exc), "code": "ROUTING_FAILED"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        if not here_routes:
            return Response(
                {"error": "No routes found for the given origin/destination.", "code": "NO_ROUTES"},
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )

        # ── Step 3: Process each route ─────────────────────────────────────
        route_results = []
        scored_routes: list[ScoredRoute] = []

        for here_route in here_routes:
            # Sample checkpoints
            checkpoints = sample_checkpoints(
                polyline=here_route.polyline,
                interval_miles=float(interval_miles),
                total_duration_seconds=here_route.duration_seconds,
                departure_time=departure_time,
            )

            # Batch fetch weather for all checkpoints
            cp_tuples = [(cp.lat, cp.lng, cp.eta) for cp in checkpoints]
            weather_list = fetch_checkpoint_weather(cp_tuples)

            # Classify risk for each checkpoint
            risk_list: list[RiskLevel] = []
            for weather in weather_list:
                risk_list.append(classify_checkpoint(weather, load_lbs))

            # Compute mile-weights for each checkpoint segment
            segment_miles = _segment_miles(checkpoints, route_distance_miles(here_route.polyline))

            # Aggregate risk summary
            risk_summary = compute_risk_summary(risk_list, segment_miles)

            # Build serialized checkpoint list
            serialized_checkpoints = [
                _serialize_checkpoint(cp, weather, risk)
                for cp, weather, risk in zip(checkpoints, weather_list, risk_list)
            ]

            distance_miles = route_distance_miles(here_route.polyline)
            duration_minutes = here_route.duration_seconds // 60

            # Score this route (rank filled later)
            scored_routes.append(
                ScoredRoute(
                    route_id=here_route.id,
                    risk_summary=risk_summary,
                    duration_minutes=duration_minutes,
                )
            )

            route_results.append({
                "id": here_route.id,
                "label": here_route.label,
                "polyline": [[lat, lng] for lat, lng in here_route.polyline],
                "checkpoints": serialized_checkpoints,
                "_risk_summary": risk_summary,
                "_distance_miles": distance_miles,
                "_duration_minutes": duration_minutes,
            })

        # ── Step 4: Rank routes ────────────────────────────────────────────
        ranked = rank_routes(scored_routes)
        rank_by_id = {r.route_id: r.rank for r in ranked}
        recommended_id = recommended_route_id(ranked)

        # ── Step 5: Assemble final response ───────────────────────────────
        routes_out = []
        for r in route_results:
            route_id = r["id"]
            routes_out.append({
                "id": route_id,
                "label": r["label"],
                "summary": _serialize_summary(
                    r["_risk_summary"],
                    r["_distance_miles"],
                    r["_duration_minutes"],
                    rank_by_id[route_id],
                ),
                "polyline": r["polyline"],
                "checkpoints": r["checkpoints"],
            })

        # Sort routes in rank order for frontend convenience
        routes_out.sort(key=lambda x: x["summary"]["rank"])

        return Response(
            {
                "recommended_route_id": recommended_id,
                "routes": routes_out,
            },
            status=status.HTTP_200_OK,
        )


# ──────────────────────────────────────────────────────────────────────────────
# HeatmapView
# ──────────────────────────────────────────────────────────────────────────────
class HeatmapView(APIView):
    """
    POST /api/heatmap/

    Accepts a bounding box and returns 49 weather intensity frames (hours 0–48).
    The frontend pre-fetches this alongside the route response; the slider
    cycles through frames client-side with zero additional network calls.
    """

    def post(self, request: Request) -> Response:
        serializer = HeatmapInputSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"error": serializer.errors},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = serializer.validated_data
        bounds = data["bounds"]
        resolution = data["grid_resolution"]

        try:
            frames = build_heatmap(bounds, resolution_deg=resolution, num_hours=49)
        except Exception as exc:
            logger.exception("Heatmap generation failed: %s", exc)
            return Response(
                {"error": "Failed to generate heatmap data.", "code": "HEATMAP_FAILED"},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        serialized_frames = [
            {
                "hour_offset": frame.hour_offset,
                "points": [
                    {"lat": p.lat, "lng": p.lng, "intensity": p.intensity}
                    for p in frame.points
                ],
            }
            for frame in frames
        ]

        return Response({"frames": serialized_frames}, status=status.HTTP_200_OK)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────
def _segment_miles(
    checkpoints: list[Checkpoint],
    total_route_miles: float,
) -> list[float]:
    """
    Assign a "representative" mile count to each checkpoint.

    Each checkpoint represents the segment from the previous checkpoint
    (or route start) to itself.  The last checkpoint absorbs any remaining miles.
    """
    if not checkpoints:
        return []

    miles = []
    prev_dist = 0.0
    for cp in checkpoints:
        miles.append(cp.distance_from_start_miles - prev_dist)
        prev_dist = cp.distance_from_start_miles

    # Add remaining tail miles to the last segment
    remaining = total_route_miles - checkpoints[-1].distance_from_start_miles
    if remaining > 0:
        miles[-1] += remaining

    return miles
