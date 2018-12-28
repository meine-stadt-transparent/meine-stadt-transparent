from django.core.management.base import BaseCommand

from importer.oparl_cli import OParlCli


class Command(BaseCommand):
    help = "Import the data of a city combining oparl with other datasources"

    def add_arguments(self, parser):
        parser.add_argument("cityname", type=str)
        parser.add_argument(
            "--mirror",
            action="store_true",
            help="Use the oparl mirror instead of the original oparl api",
        )

    def handle(self, *args, **options):
        oparl_cli = OParlCli()
        oparl_cli.from_userinput(options["cityname"], options["mirror"])
