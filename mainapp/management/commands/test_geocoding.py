import logging

from django.core.management import BaseCommand, CommandError

from mainapp.functions.geo_functions import geocode

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument(
            "--search-str", default="Marienplatz 1, München, Deutschland"
        )

    def handle(self, *args, **options):
        search_str = options["search_str"]
        geometry = geocode(search_str)
        if not geometry:
            raise CommandError("Geocoding failed")
        elif geometry["type"] == "Point":
            logger.info(f"Success! Geometry for '{search_str}': {geometry}")
        else:
            raise CommandError(
                f"Wrong geometry returned for '{search_str}': {geometry}"
            )
