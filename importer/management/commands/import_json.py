import datetime
import json
import logging
from pathlib import Path

from dateutil import tz
from django.conf import settings
from django.core.management import BaseCommand, CommandParser, CommandError

from importer.functions import fix_sort_date
from importer.import_json import import_data
from importer.importer import Importer
from importer.json_datatypes import RisData, converter, format_version
from importer.loader import BaseLoader
from mainapp import models
from mainapp.functions.city_to_ags import city_to_ags
from mainapp.functions.citytools import import_outline, import_streets
from mainapp.functions.notify_users import NotifyUsers

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Imports a municipality from a json file"

    def add_arguments(self, parser: CommandParser):
        # noinspection PyTypeChecker
        parser.add_argument("input", type=Path, help="Path to the json file")
        parser.add_argument("--ags", help="The Amtliche Gemeindeschlüssel")
        parser.add_argument(
            "--skip-download",
            action="store_true",
            dest="skip_download",
            default=False,
            help="Do not download and parse the files",
        )
        parser.add_argument(
            "--skip-body-extra",
            action="store_true",
            dest="skip_body_extra",
            default=False,
            help="Do not download streets and shape of the body",
        )
        parser.add_argument(
            "--no-notify-users",
            action="store_true",
            dest="no_notify_users",
            default=False,
            help="Don't send notifications",
        )
        parser.add_argument(
            "--allow-shrinkage",
            action="store_true",
            dest="allow_shrinkage",
            default=False,
            help="Don't fail when trying to import a smaller dataset over a bigger existing one",
        )

    def handle(self, *args, **options):
        input_file: Path = options["input"]

        logger.info("Loading the data")
        with input_file.open() as fp:
            json_data = json.load(fp)
            if json_data["format_version"] != format_version:
                raise CommandError(
                    f"This version of {settings.PRODUCT_NAME} can only import json format version {format_version}, "
                    f"but the json file you provided is version {json_data['format_version']}"
                )
            ris_data: RisData = converter.structure(json_data, RisData)

        body = models.Body.objects.filter(name=ris_data.meta.name).first()
        if not body:
            logger.info("Building the body")

            if options["ags"] or ris_data.meta.ags:
                ags = options["ags"] or ris_data.meta.ags
            else:
                ags = city_to_ags(ris_data.meta.name, False)
                if not ags:
                    raise RuntimeError(
                        f"Failed to determine the Amtliche Gemeindeschlüssel for '{ris_data.meta.name}'. "
                        f"Please look it up yourself and specify it with `--ags`"
                    )
                logger.info(f"The Amtliche Gemeindeschlüssel is {ags}")
            body = models.Body(
                name=ris_data.meta.name, short_name=ris_data.meta.name, ags=ags
            )
            body.save()
            if not options["skip_body_extra"]:
                import_outline(body)
                import_streets(body)
        else:
            logging.info("Using existing body")

        # TODO: Re-enable this after some more thorough testing
        # handle_counts(ris_data, options["allow_shrinkage"])

        import_data(body, ris_data)

        fix_sort_date(datetime.datetime.now(tz=tz.tzlocal()))

        if not options["skip_download"]:
            Importer(BaseLoader(dict()), force_singlethread=True).load_files(
                fallback_city=settings.GEOEXTRACT_SEARCH_CITY or body.short_name
            )

        if not options["no_notify_users"]:
            logger.info("Sending notifications")
            NotifyUsers().notify_all()
