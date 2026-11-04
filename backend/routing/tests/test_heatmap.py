"""
Unit tests for the heatmap service.

Tests cover:
- Grid point generation (resolution, edge cases)
- build_heatmap frame count and structure
- compute_heatmap_intensity clamping and weighting
- Empty/degenerate bounds handling
"""
from __future__ import annotations

from unittest.mock import patch

import pytest

from routing.services.heatmap import HeatmapFrame, HeatmapPoint, _arange, _build_grid, build_heatmap
from routing.services.risk import WeatherData, compute_heatmap_intensity


# ─────────────────────────────────────────────────────────────────────────────
# _arange helper
# ─────────────────────────────────────────────────────────────────────────────
class TestArange:
    def test_basic_range(self):
        values = _arange(0.0, 1.0, 0.5)
        assert values == [0.0, 0.5, 1.0]

    def test_single_value(self):
        values = _arange(5.0, 5.0, 1.0)
        assert len(values) == 1
        assert values[0] == pytest.approx(5.0)

    def test_fractional_step(self):
        values = _arange(39.0, 41.0, 1.0)
        assert len(values) == 3   # 39, 40, 41
        assert values[0] == pytest.approx(39.0)
        assert values[-1] == pytest.approx(41.0)

    def test_stop_exclusive_beyond_range(self):
        # Should not generate values beyond stop
        values = _arange(0.0, 0.9, 0.5)
        assert all(v <= 0.9 + 1e-6 for v in values)


# ─────────────────────────────────────────────────────────────────────────────
# _build_grid
# ─────────────────────────────────────────────────────────────────────────────
class TestBuildGrid:
    def test_basic_grid_size(self):
        bounds = {"north": 42.0, "south": 40.0, "east": -85.0, "west": -87.0}
        grid = _build_grid(bounds, resolution=1.0)
        # lats: 40, 41, 42 = 3; lngs: -87, -86, -85 = 3 → 9 points
        assert len(grid) == 9

    def test_returns_tuples(self):
        bounds = {"north": 42.0, "south": 40.0, "east": -85.0, "west": -87.0}
        grid = _build_grid(bounds, resolution=1.0)
        for item in grid:
            assert len(item) == 2
            lat, lng = item
            assert 40.0 <= lat <= 42.0
            assert -87.0 <= lng <= -85.0

    def test_invalid_bounds_returns_empty(self):
        # south > north
        bounds = {"north": 39.0, "south": 42.0, "east": -85.0, "west": -87.0}
        grid = _build_grid(bounds, resolution=1.0)
        assert grid == []

    def test_invalid_east_west_returns_empty(self):
        # east < west
        bounds = {"north": 42.0, "south": 40.0, "east": -90.0, "west": -85.0}
        grid = _build_grid(bounds, resolution=1.0)
        assert grid == []

    def test_finer_resolution_gives_more_points(self):
        bounds = {"north": 42.0, "south": 40.0, "east": -85.0, "west": -87.0}
        coarse = _build_grid(bounds, resolution=1.0)
        fine = _build_grid(bounds, resolution=0.5)
        assert len(fine) > len(coarse)

    def test_rounding_applied(self):
        bounds = {"north": 42.0, "south": 40.0, "east": -85.0, "west": -87.0}
        grid = _build_grid(bounds, resolution=0.25)
        for lat, lng in grid:
            # Coordinates should have at most 4 decimal places
            assert round(lat, 4) == lat
            assert round(lng, 4) == lng


# ─────────────────────────────────────────────────────────────────────────────
# compute_heatmap_intensity (from risk module)
# ─────────────────────────────────────────────────────────────────────────────
class TestComputeHeatmapIntensity:
    def test_calm_weather_near_zero(self):
        weather = WeatherData(
            wind_speed_mph=5.0,
            rain_in_hr=0.0,
            snow_in_hr=0.0,
            temperature_f=60.0,
            weather_code=0,
        )
        intensity = compute_heatmap_intensity(weather)
        assert 0.0 <= intensity <= 0.2

    def test_severe_wind_gives_high_intensity(self):
        weather = WeatherData(
            wind_speed_mph=55.0,
            rain_in_hr=0.0,
            snow_in_hr=0.0,
            temperature_f=40.0,
            weather_code=0,
        )
        intensity = compute_heatmap_intensity(weather)
        assert intensity == pytest.approx(1.0)

    def test_heavy_rain_gives_high_intensity(self):
        weather = WeatherData(
            wind_speed_mph=10.0,
            rain_in_hr=1.5,   # > max threshold of 1.0
            snow_in_hr=0.0,
            temperature_f=55.0,
            weather_code=61,
        )
        intensity = compute_heatmap_intensity(weather)
        assert intensity == pytest.approx(1.0)

    def test_heavy_snow_gives_high_intensity(self):
        weather = WeatherData(
            wind_speed_mph=10.0,
            rain_in_hr=0.0,
            snow_in_hr=4.0,   # > max threshold of 3.0
            temperature_f=28.0,
            weather_code=73,
        )
        intensity = compute_heatmap_intensity(weather)
        assert intensity == pytest.approx(1.0)

    def test_intensity_clamped_to_one(self):
        weather = WeatherData(
            wind_speed_mph=200.0,  # way beyond scale
            rain_in_hr=10.0,
            snow_in_hr=20.0,
            temperature_f=0.0,
            weather_code=99,
        )
        intensity = compute_heatmap_intensity(weather)
        assert intensity <= 1.0

    def test_intensity_non_negative(self):
        weather = WeatherData(
            wind_speed_mph=0.0,
            rain_in_hr=0.0,
            snow_in_hr=0.0,
            temperature_f=75.0,
            weather_code=0,
        )
        intensity = compute_heatmap_intensity(weather)
        assert intensity >= 0.0

    def test_moderate_mixed_conditions(self):
        weather = WeatherData(
            wind_speed_mph=27.5,   # ~50% of 55
            rain_in_hr=0.5,        # 50% of 1.0
            snow_in_hr=0.0,
            temperature_f=42.0,
            weather_code=61,
        )
        intensity = compute_heatmap_intensity(weather)
        # Should be dominated by the max of the three scores
        assert 0.3 < intensity < 0.8


# ─────────────────────────────────────────────────────────────────────────────
# build_heatmap (integration, weather mocked)
# ─────────────────────────────────────────────────────────────────────────────
class TestBuildHeatmap:
    BOUNDS = {"north": 42.0, "south": 40.0, "east": -85.0, "west": -87.0}

    def _make_weather_matrix(self, n_points: int, n_hours: int) -> list[list[WeatherData]]:
        """Return a stable weather matrix with mild conditions."""
        mild = WeatherData(
            wind_speed_mph=15.0, rain_in_hr=0.0, snow_in_hr=0.0,
            temperature_f=55.0, weather_code=0,
        )
        return [[mild] * n_hours for _ in range(n_points)]

    @patch("routing.services.heatmap.fetch_heatmap_weather")
    def test_returns_correct_number_of_frames(self, mock_weather):
        mock_weather.side_effect = lambda pts, num_hours: self._make_weather_matrix(len(pts), num_hours)

        frames = build_heatmap(self.BOUNDS, resolution_deg=1.0, num_hours=49)
        assert len(frames) == 49

    @patch("routing.services.heatmap.fetch_heatmap_weather")
    def test_frame_hour_offsets_are_sequential(self, mock_weather):
        mock_weather.side_effect = lambda pts, num_hours: self._make_weather_matrix(len(pts), num_hours)

        frames = build_heatmap(self.BOUNDS, resolution_deg=1.0, num_hours=5)
        for i, frame in enumerate(frames):
            assert frame.hour_offset == i

    @patch("routing.services.heatmap.fetch_heatmap_weather")
    def test_frames_contain_only_nonzero_intensity_points(self, mock_weather):
        mock_weather.side_effect = lambda pts, num_hours: self._make_weather_matrix(len(pts), num_hours)

        frames = build_heatmap(self.BOUNDS, resolution_deg=1.0, num_hours=3)
        for frame in frames:
            for pt in frame.points:
                assert pt.intensity > 0.01

    @patch("routing.services.heatmap.fetch_heatmap_weather")
    def test_points_include_lat_lng_intensity(self, mock_weather):
        mock_weather.side_effect = lambda pts, num_hours: self._make_weather_matrix(len(pts), num_hours)

        frames = build_heatmap(self.BOUNDS, resolution_deg=1.0, num_hours=1)
        assert len(frames) == 1
        for pt in frames[0].points:
            assert hasattr(pt, "lat")
            assert hasattr(pt, "lng")
            assert hasattr(pt, "intensity")

    @patch("routing.services.heatmap.fetch_heatmap_weather")
    def test_calm_weather_filters_most_points(self, mock_weather):
        """Points with near-zero intensity should be excluded."""
        calm = WeatherData(
            wind_speed_mph=0.0, rain_in_hr=0.0, snow_in_hr=0.0,
            temperature_f=70.0, weather_code=0,
        )
        # Return a matrix sized to actual grid: bounds 40–42 × -87–-85 @ res=1.0
        # After 0.5° padding: 39.5–42.5 × -87.5–-84.5 → lats=[39.5,40.5,41.5,42.5], lngs same → 16 points
        mock_weather.side_effect = lambda pts, num_hours: [[calm] * num_hours for _ in pts]

        frames = build_heatmap(self.BOUNDS, resolution_deg=1.0, num_hours=1)
        # All points should be filtered out (intensity ~0)
        assert all(len(f.points) == 0 for f in frames)

    def test_empty_bounds_returns_empty(self):
        bad_bounds = {"north": 40.0, "south": 42.0, "east": -85.0, "west": -87.0}
        frames = build_heatmap(bad_bounds, resolution_deg=1.0, num_hours=3)
        assert frames == []

    @patch("routing.services.heatmap.fetch_heatmap_weather")
    def test_coarser_resolution_fetches_fewer_points(self, mock_weather):
        call_counts = []

        def side_effect(pts, num_hours):
            call_counts.append(len(pts))
            return self._make_weather_matrix(len(pts), num_hours)

        mock_weather.side_effect = side_effect

        build_heatmap(self.BOUNDS, resolution_deg=0.5, num_hours=1)
        fine_count = call_counts[-1]

        mock_weather.side_effect = side_effect
        build_heatmap(self.BOUNDS, resolution_deg=1.0, num_hours=1)
        coarse_count = call_counts[-1]

        assert fine_count > coarse_count

    @patch("routing.services.heatmap.fetch_heatmap_weather")
    def test_bounding_box_is_padded(self, mock_weather):
        """build_heatmap should pad bounds by _BOUNDS_PADDING_DEG."""
        captured = {}

        def side_effect(pts, num_hours):
            captured["pts"] = pts
            return self._make_weather_matrix(len(pts), num_hours)

        mock_weather.side_effect = side_effect

        tight_bounds = {"north": 41.0, "south": 41.0, "east": -86.0, "west": -86.0}
        build_heatmap(tight_bounds, resolution_deg=0.5, num_hours=1)

        if captured.get("pts"):
            lats = [p[0] for p in captured["pts"]]
            lngs = [p[1] for p in captured["pts"]]
            # After padding, range should extend beyond the tight bounds
            assert max(lats) > 41.0
            assert min(lats) < 41.0
