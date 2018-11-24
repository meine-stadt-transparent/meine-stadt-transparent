import logging

from django.core.management.base import BaseCommand

from importer.amenities import Importamenities
from mainapp.models import Body

logger = logging.getLogger(__name__)


class Command(BaseCommand, Importamenities):
    help = "Imports amenities from OpenStreetMap for a given city (amtlicher_gemeindeschluessel=gemeideschlüssel)"

    def add_arguments(self, parser):
        parser.add_argument("gemeindeschluessel", type=str)
        parser.add_argument("amenity", type=str)
        parser.add_argument("body-id", type=int)

    def handle(self, *args, **options):
        body = Body.objects.get(id=options["body-id"])

        self.importamenities(body, options["gemeindeschluessel"], options["amenity"])
