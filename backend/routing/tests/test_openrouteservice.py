"""
Unit tests for the OpenRouteService routing and geocoding integration.
"""
from unittest.mock import patch, MagicMock
import pytest
from routing.services.openrouteservice import (
    ORSRoute,
    ORSError,
    geocode,
    fetch_routes,
    _ensure_three_alternatives,
    _generate_fallback_corridors,
)


class TestGeocode:
    @patch("httpx.get")
    def test_ors_geocode_success(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "features": [
                {
                    "geometry": {
                        "coordinates": [-87.6298, 41.8781]  # [lng, lat]
                    }
                }
            ]
        }
        mock_get.return_value = mock_resp

        lat, lng = geocode("Chicago, IL")
        assert lat == pytest.approx(41.8781)
        assert lng == pytest.approx(-87.6298)

    @patch("httpx.get")
    def test_nominatim_fallback(self, mock_get):
        # First call (ORS) fails, second call (Nominatim) succeeds
        ors_fail = MagicMock()
        ors_fail.status_code = 401

        nom_ok = MagicMock()
        nom_ok.status_code = 200
        nom_ok.json.return_value = [{"lat": "32.7767", "lon": "-96.7970"}]

        mock_get.side_effect = [ors_fail, nom_ok]

        lat, lng = geocode("Dallas, TX")
        assert lat == pytest.approx(32.7767)
        assert lng == pytest.approx(-96.7970)

    def test_known_city_fallback(self):
        with patch("httpx.get", side_effect=Exception("Network down")):
            lat, lng = geocode("Denver, CO")
            assert lat == pytest.approx(39.7392)
            assert lng == pytest.approx(-104.9903)


class TestFetchRoutes:
    @patch("routing.services.openrouteservice.get_ors_api_key", return_value="test-api-key")
    @patch("httpx.post")
    def test_ors_directions_geojson_success(self, mock_post, mock_key):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "type": "FeatureCollection",
            "features": [
                {
                    "geometry": {
                        "coordinates": [
                            [-87.6298, 41.8781],
                            [-87.0, 41.0],
                            [-86.1581, 39.7684],
                        ]
                    },
                    "properties": {
                        "summary": {
                            "distance": 290000,
                            "duration": 10800,
                        }
                    },
                }
            ],
        }
        mock_post.return_value = mock_resp

        routes = fetch_routes(41.8781, -87.6298, 39.7684, -86.1581)
        assert len(routes) == 3  # Automatically generates 3 alternatives if ORS returns 1
        assert routes[0].label == "Route A"
        assert routes[1].label == "Route B"
        assert routes[2].label == "Route C"
        assert routes[0].distance_meters == 290000
        assert routes[0].duration_seconds == 10800

    def test_fallback_corridors(self):
        routes = _generate_fallback_corridors(41.8781, -87.6298, 39.7684, -86.1581)
        assert len(routes) == 3
        assert routes[0].label == "Route A"
        assert len(routes[0].polyline) >= 10
        assert routes[0].polyline[0] == pytest.approx((41.8781, -87.6298), rel=1e-3)
        assert routes[0].polyline[-1] == pytest.approx((39.7684, -86.1581), rel=1e-3)

    def test_ensure_three_alternatives_pads_when_fewer(self):
        base_route = ORSRoute(
            id="route_0",
            label="Route A",
            polyline=[(40.0, -80.0), (41.0, -81.0), (42.0, -82.0)],
            distance_meters=100000,
            duration_seconds=3600,
        )
        padded = _ensure_three_alternatives([base_route], 40.0, -80.0, 42.0, -82.0)
        assert len(padded) == 3
        assert padded[0].id == "route_0"
        assert padded[1].id == "route_1"
        assert padded[2].id == "route_2"
