from django.core.management.base import BaseCommand

from importer.oparl_auto import OParlAuto


class Command(BaseCommand):
    help = 'Import the data of a city combining oparl with other datasources'

    def add_arguments(self, parser, add_entrypoint=True):
        parser.add_argument('cityname', type=str)

    def handle(self, *args, **options):
        OParlAuto.magic_import(options["cityname"])
