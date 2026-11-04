"""
DRF serializers for input validation and output shaping.
"""
from __future__ import annotations

from datetime import datetime, timezone

from rest_framework import serializers

VALID_INTERVALS = [10, 25, 50]


# ──────────────────────────────────────────────────────────────────────────────
# Input serializers
# ──────────────────────────────────────────────────────────────────────────────
class RouteInputSerializer(serializers.Serializer):
    origin = serializers.CharField(max_length=200)
    destination = serializers.CharField(max_length=200)
    departure_time = serializers.DateTimeField()
    load_weight_lbs = serializers.FloatField(min_value=0, max_value=200_000)
    checkpoint_interval_miles = serializers.ChoiceField(choices=VALID_INTERVALS, default=25)

    def validate_departure_time(self, value: datetime) -> datetime:
        # Accept naive datetimes (assume UTC)
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value

    def validate_origin(self, value: str) -> str:
        if value.strip() == "":
            raise serializers.ValidationError("origin cannot be blank.")
        return value.strip()

    def validate_destination(self, value: str) -> str:
        if value.strip() == "":
            raise serializers.ValidationError("destination cannot be blank.")
        return value.strip()


class HeatmapInputSerializer(serializers.Serializer):
    class BoundsSerializer(serializers.Serializer):
        north = serializers.FloatField(min_value=-90, max_value=90)
        south = serializers.FloatField(min_value=-90, max_value=90)
        east = serializers.FloatField(min_value=-180, max_value=180)
        west = serializers.FloatField(min_value=-180, max_value=180)

        def validate(self, data):
            if data["south"] >= data["north"]:
                raise serializers.ValidationError("south must be less than north.")
            if data["west"] >= data["east"]:
                raise serializers.ValidationError("west must be less than east.")
            return data

    bounds = BoundsSerializer()
    departure_time = serializers.DateTimeField()
    grid_resolution = serializers.FloatField(min_value=0.1, max_value=2.0, default=0.25)
