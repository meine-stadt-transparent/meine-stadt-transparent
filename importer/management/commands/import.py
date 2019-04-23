from django.core.management.base import BaseCommand

from importer.cli import Cli


class Command(BaseCommand):
    help = "Import the data of a city combining oparl with other datasources"

    def add_arguments(self, parser):
        parser.add_argument("cityname")
        parser.add_argument(
            "--mirror",
            action="store_true",
            help="Use the oparl mirror instead of the original oparl api",
        )

    def handle(self, *args, **options):
        cli = Cli()
        cli.from_userinput(options["cityname"], options["mirror"])
