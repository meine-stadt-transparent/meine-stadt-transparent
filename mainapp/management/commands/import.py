from django.core.management.base import BaseCommand

from importer.oparl_cli import OParlCli


class Command(BaseCommand):
    help = "Import the data of a city combining oparl with other datasources"

    def add_arguments(self, parser, add_entrypoint=True):
        parser.add_argument("cityname", type=str)

    def handle(self, *args, **options):
        OParlCli.from_userinput(options["cityname"])
