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
        parser.add_argument(
            "--skip-body-extra",
            action="store_true",
            dest="skip_body_extra",
            default=False,
            help="Do not download streets and shape of the body",
        )
        parser.add_argument(
            "--skip-files",
            action="store_true",
            dest="skip_files",
            default=False,
            help="Do not download the files",
        )
        parser.add_argument("--ags", help="The Amtliche Gemeindeschlüssel")

    def handle(self, *args, **options):
        cli = Cli()
        cli.from_userinput(
            options["cityname"],
            options["mirror"],
            options["ags"],
            skip_body_extra=options["skip_body_extra"],
            skip_files=options["skip_files"],
        )
