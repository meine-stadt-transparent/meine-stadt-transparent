from django.core.management.base import BaseCommand

from importer.citytools import import_outline


class Command(BaseCommand):
    help = 'Imports the outlines from OpenStreetMap for a given city (amtlicher_gemeindeschluessel=gemeideschlüssel)'

    def add_arguments(self, parser):
        parser.add_argument('gemeindeschluessel', type=str)
        parser.add_argument('body-id', type=int)
        parser.add_argument('--tmpfile', type=str, default='/tmp/city-outline.json')

    def handle(self, *args, **options):
        import_outline(options["body-id"], options["gemeindeschluessel"], options["tmpfile"])
