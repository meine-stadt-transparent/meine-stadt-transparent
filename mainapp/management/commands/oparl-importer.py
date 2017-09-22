from django.core.management.base import BaseCommand

from importer import OparlImporter


class Command(BaseCommand):
    help = 'Import the data from an oparl api into '

    def add_arguments(self, parser):
        parser.add_argument('entrypoint', type=str)

    def handle(self, *args, **options):
        OparlImporter(options['entrypoint']).run()
