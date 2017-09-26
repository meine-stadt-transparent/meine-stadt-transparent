from django.core.management.base import BaseCommand

from importer import OParlImporter


class Command(BaseCommand):
    help = 'Import the data from an oparl api into '

    def add_arguments(self, parser):
        parser.add_argument('entrypoint', type=str)
        parser.add_argument('--cachefolder', type=str, default="/tmp/import-oparl-cache")
        parser.add_argument('--storagefolder', type=str, default="./import-storage")

    def handle(self, *args, **options):
        OParlImporter(options['entrypoint'], options['cachefolder'], options["storagefolder"]).run()
