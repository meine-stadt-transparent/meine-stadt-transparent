import logging

from django.core.management.base import BaseCommand
from tqdm import tqdm

from mainapp.functions.geo_functions import geocode
from mainapp.models import Location

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Tries to geocode all locations without coordinates, e.g. because geocoding failed before."

    def handle(self, *args, **options):
        without_geometry = Location.objects.filter(
            geometry=None, search_str__isnull=False
        )
        total = without_geometry.count()
        fixed = 0
        for location in tqdm(without_geometry.all(), total=total):
            geometry = geocode(location.search_str)
            if geometry:
                location.geometry = geometry
                location.save()
                fixed += 1
        logger.info(f"Fixed {fixed} of {total}")
