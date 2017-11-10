from django.core.management.base import BaseCommand

from importer.citytools import import_streets


class Command(BaseCommand):
    help = 'Imports streets from OpenStreetMap for a given city (amtlicher_gemeindeschluessel=gemeideschlüssel)'

    def add_arguments(self, parser):
        parser.add_argument('gemeindeschluessel', type=str)
        parser.add_argument('body-id', type=int)

    def handle(self, *args, **options):
        import_streets(options["body-id"], options['gemeindeschluessel'])
