"""Database models for canonical GeoEstate property listings."""

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class Property(models.Model):
    """A cleaned property listing ready for future geospatial enrichment."""

    property_id = models.CharField(primary_key=True, max_length=24, editable=False)
    title = models.CharField(max_length=255, blank=True)
    location = models.CharField(max_length=255, db_index=True)
    price_lakh = models.DecimalField(max_digits=14, decimal_places=2)
    rate_per_sqft = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    area_sqft = models.PositiveIntegerField()
    building_status = models.CharField(max_length=100, blank=True)
    bedrooms = models.PositiveSmallIntegerField(null=True, blank=True)

    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    investment_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    connectivity_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    green_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    liveability_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True, validators=[MinValueValidator(0), MaxValueValidator(100)])
    nearest_metro = models.CharField(max_length=255, null=True, blank=True)
    nearest_hospital = models.CharField(max_length=255, null=True, blank=True)
    nearest_school = models.CharField(max_length=255, null=True, blank=True)
    ai_summary = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "properties"
        ordering = ("location", "property_id")
        indexes = [
            models.Index(fields=["location", "price_lakh"], name="property_location_price_idx"),
        ]

    def __str__(self) -> str:
        """Return an admin-friendly listing identifier."""
        return f"{self.title or 'Property'} — {self.location} ({self.property_id})"
