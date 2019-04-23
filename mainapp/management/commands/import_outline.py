from django.core.management.base import BaseCommand

from mainapp.functions.citytools import import_outline
from mainapp.models import Body


class Command(BaseCommand):
    help = "Imports the outlines from OpenStreetMap for a given city (amtlicher_gemeindeschluessel=gemeideschlüssel)"

    def add_arguments(self, parser):
        parser.add_argument("gemeindeschluessel", type=str)
        parser.add_argument("body-id", type=int)

    def handle(self, *args, **options):
        body = Body.objects.get(id=options["body-id"])

        import_outline(body, options["gemeindeschluessel"])
