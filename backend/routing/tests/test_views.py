"""
Integration tests for RouteView and HeatmapView with mocked external services.
"""
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from routing.services.here import HereRoute
from routing.services.risk import WeatherData


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def valid_route_payload():
    return {
        "origin": "Chicago, IL",
        "destination": "Indianapolis, IN",
        "departure_time": "2026-11-04T08:00:00Z",
        "load_weight_lbs": 35000,
        "checkpoint_interval_miles": 25,
    }


@pytest.fixture
def mock_here_routes():
    # 2 simple routes
    # polyline spanning ~100 miles
    coords1 = [(41.85, -87.65), (41.0, -87.0), (39.77, -86.16)]
    coords2 = [(41.85, -87.65), (40.5, -86.8), (39.77, -86.16)]
    return [
        HereRoute(
            id="route_0",
            label="Route A",
            polyline=coords1,
            distance_meters=290000,
            duration_seconds=10800,
        ),
        HereRoute(
            id="route_1",
            label="Route B",
            polyline=coords2,
            distance_meters=310000,
            duration_seconds=12000,
        ),
    ]


@pytest.fixture
def mock_weather():
    return WeatherData(
        wind_speed_mph=20.0,
        rain_in_hr=0.0,
        snow_in_hr=0.0,
        temperature_f=60.0,
        weather_code=0,
    )


@pytest.mark.django_db
class TestRouteView:
    @patch("routing.views.fetch_checkpoint_weather")
    @patch("routing.views.fetch_routes")
    @patch("routing.views.geocode")
    def test_successful_route_request(
        self,
        mock_geocode,
        mock_fetch_routes,
        mock_fetch_weather,
        api_client,
        valid_route_payload,
        mock_here_routes,
        mock_weather,
    ):
        mock_geocode.side_effect = [(41.85, -87.65), (39.77, -86.16)]
        mock_fetch_routes.return_value = mock_here_routes
        mock_fetch_weather.side_effect = lambda cps: [mock_weather for _ in cps]

        url = reverse("routes")
        response = api_client.post(url, valid_route_payload, format="json")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "recommended_route_id" in data
        assert "routes" in data
        assert len(data["routes"]) == 2
        
        route0 = data["routes"][0]
        assert "summary" in route0
        assert "checkpoints" in route0
        assert "polyline" in route0
        assert route0["summary"]["rank"] == 1

    def test_missing_fields_validation_error(self, api_client):
        url = reverse("routes")
        response = api_client.post(url, {}, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
        data = response.json()
        assert "error" in data

    def test_invalid_interval_choice(self, api_client, valid_route_payload):
        valid_route_payload["checkpoint_interval_miles"] = 15
        url = reverse("routes")
        response = api_client.post(url, valid_route_payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @patch("routing.views.geocode")
    def test_geocoding_failure_handling(self, mock_geocode, api_client, valid_route_payload):
        from routing.services.here import HereAPIError
        mock_geocode.side_effect = HereAPIError("Location not found")

        url = reverse("routes")
        response = api_client.post(url, valid_route_payload, format="json")
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert response.json()["code"] == "GEOCODING_FAILED"


@pytest.mark.django_db
class TestHeatmapView:
    @patch("routing.views.build_heatmap")
    def test_successful_heatmap_request(self, mock_build_heatmap, api_client):
        from routing.services.heatmap import HeatmapFrame, HeatmapPoint
        mock_build_heatmap.return_value = [
            HeatmapFrame(
                hour_offset=0,
                points=[HeatmapPoint(lat=41.0, lng=-87.0, intensity=0.5)],
            )
        ]

        url = reverse("heatmap")
        payload = {
            "bounds": {
                "north": 42.0,
                "south": 39.0,
                "east": -85.0,
                "west": -88.0,
            },
            "departure_time": "2026-11-04T08:00:00Z",
            "grid_resolution": 0.5,
        }
        response = api_client.post(url, payload, format="json")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "frames" in data
        assert len(data["frames"]) == 1
        assert data["frames"][0]["points"][0]["intensity"] == 0.5

    def test_invalid_bounds(self, api_client):
        url = reverse("heatmap")
        payload = {
            "bounds": {
                "north": 39.0,
                "south": 42.0,  # south > north
                "east": -85.0,
                "west": -88.0,
            },
            "departure_time": "2026-11-04T08:00:00Z",
        }
        response = api_client.post(url, payload, format="json")
        assert response.status_code == status.HTTP_400_BAD_REQUEST
