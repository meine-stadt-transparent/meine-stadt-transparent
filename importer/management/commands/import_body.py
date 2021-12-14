import logging

from django.core.management.base import BaseCommand

from importer.cli import Cli
from importer.importer import Importer
from importer.loader import get_loader_from_system
from importer.models import CachedObject

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Imports the body you gave by name or url, meaning creating the body itself and some metadata, "
        "but not loading or importing the bulk of the other data"
    )

    def add_arguments(self, parser):
        parser.add_argument("cityname")
        parser.add_argument("--ags", help="The Amtliche Gemeindeschlüssel")
        parser.add_argument(
            "--mirror",
            action="store_true",
            help="Use the oparl mirror instead of the original oparl api",
        )
        parser.add_argument(
            "--manual",
            action="store_true",
            help="Do not attempt to import metadata such as ags, streets and outline",
        )

    def handle(self, *args, **options):
        cli = Cli()
        userinput = options["cityname"]
        body_id, entrypoint = cli.get_entrypoint_and_body(userinput, options["mirror"])
        importer = Importer(get_loader_from_system(entrypoint))
        if options["manual"]:
            if CachedObject.objects.filter(url=body_id).exists():
                logger.info("Using fetched body")

            else:
                logger.info("Fetching the body")
                importer.load_bodies(body_id)
            logger.info("Importing the body")
            [body] = importer.import_bodies()
            logger.info(f"The body id is {body.id}")
        else:
            cli.import_body_and_metadata(body_id, importer, userinput, options["ags"])
