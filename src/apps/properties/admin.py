"""Admin registration for imported property listings."""

from django.contrib import admin

from .models import Property


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    """Operational admin view for imported property records."""

    list_display = ("property_id", "title", "location", "price_lakh", "area_sqft", "bedrooms", "building_status")
    list_filter = ("building_status", "bedrooms")
    search_fields = ("property_id", "title", "location")
    readonly_fields = ("property_id", "created_at", "updated_at")
    ordering = ("location", "property_id")
