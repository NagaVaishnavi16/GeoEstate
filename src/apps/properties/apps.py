"""Django application configuration for the property domain."""

from django.apps import AppConfig


class PropertiesConfig(AppConfig):
    """Configure the GeoEstate property application."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.properties"
    verbose_name = "GeoEstate Properties"
