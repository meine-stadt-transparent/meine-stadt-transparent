import logging

from django.core.management import BaseCommand, CommandError

from mainapp.functions.geo_functions import geocode
from pytest import approx
logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        search_str = "Marienplatz 1, München, Deutschland"
        geometry = geocode(search_str)
        if not geometry:
            raise CommandError("Geocoding failed")
        elif geometry == {"type": "Point", "coordinates": [approx(11.5748977), approx(48.1375615)]}:
            logger.info(f"Success! Geometry for '{search_str}': {geometry}")
        else:
            raise CommandError(f"Wrong geometry returned for '{search_str}': {geometry}")
