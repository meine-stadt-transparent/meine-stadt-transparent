import logging

from django.core.management.base import BaseCommand

from mainapp.functions.amenities import import_amenities
from mainapp.models import Body

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Imports amenities from OpenStreetMap for a given city (amtlicher_gemeindeschluessel=gemeideschlüssel)"

    def add_arguments(self, parser):
        parser.add_argument("gemeindeschluessel", type=str)
        parser.add_argument("amenity", type=str)
        parser.add_argument("body-id", type=int)

    def handle(self, *args, **options):
        body = Body.objects.get(id=options["body-id"])

        import_amenities(body, options["gemeindeschluessel"], options["amenity"])
