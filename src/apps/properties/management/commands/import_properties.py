"""Import a processed GeoEstate property CSV into PostgreSQL."""

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.properties.services import PropertyImportError, PropertyImportService


class Command(BaseCommand):
    """Load the canonical processed property CSV using idempotent upserts."""

    help = "Import processed_hyderabad_properties.csv into the properties table."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--file",
            type=Path,
            default=settings.BASE_DIR / "outputs" / "processed_hyderabad_properties.csv",
            help="Path to a canonical processed property CSV.",
        )
        parser.add_argument("--batch-size", type=int, default=500, help="Rows per PostgreSQL upsert batch.")

    def handle(self, *args, **options) -> None:
        try:
            result = PropertyImportService(options["file"], options["batch_size"]).import_data()
        except (PropertyImportError, ValueError) as error:
            raise CommandError(str(error)) from error
        self.stdout.write(self.style.SUCCESS(f"Imported {result.rows_processed} property rows from {result.source_path}."))
