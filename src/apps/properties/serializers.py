"""API serializers for read-only property representations."""

from rest_framework import serializers

from .models import Property


class PropertySerializer(serializers.ModelSerializer):
    """Expose the canonical property schema through the REST API."""

    class Meta:
        model = Property
        fields = (
            "property_id", "title", "location", "price_lakh", "rate_per_sqft", "area_sqft",
            "building_status", "bedrooms", "latitude", "longitude", "investment_score",
            "connectivity_score", "green_score", "liveability_score", "nearest_metro",
            "nearest_hospital", "nearest_school", "ai_summary",
        )
        read_only_fields = fields
