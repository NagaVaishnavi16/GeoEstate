# Generated manually for the GeoEstate property domain.

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Property",
            fields=[
                ("property_id", models.CharField(editable=False, max_length=24, primary_key=True, serialize=False)),
                ("title", models.CharField(blank=True, max_length=255)),
                ("location", models.CharField(db_index=True, max_length=255)),
                ("price_lakh", models.DecimalField(decimal_places=2, max_digits=14)),
                ("rate_per_sqft", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True)),
                ("area_sqft", models.PositiveIntegerField()),
                ("building_status", models.CharField(blank=True, max_length=100)),
                ("bedrooms", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("latitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("longitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("investment_score", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ("connectivity_score", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ("green_score", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ("liveability_score", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True, validators=[django.core.validators.MinValueValidator(0), django.core.validators.MaxValueValidator(100)])),
                ("nearest_metro", models.CharField(blank=True, max_length=255, null=True)),
                ("nearest_hospital", models.CharField(blank=True, max_length=255, null=True)),
                ("nearest_school", models.CharField(blank=True, max_length=255, null=True)),
                ("ai_summary", models.TextField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "properties",
                "ordering": ("location", "property_id"),
            },
        ),
        migrations.AddIndex(
            model_name="property",
            index=models.Index(fields=["location", "price_lakh"], name="property_location_price_idx"),
        ),
    ]
