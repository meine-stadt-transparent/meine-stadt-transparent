import logging
from abc import ABC
from typing import Tuple, Dict, Any

from django.conf import settings
from django.core.management.base import BaseCommand

from importer.importer import Importer
from importer.loader import get_loader_from_body, BaseLoader
from mainapp.models import Body

logger = logging.getLogger(__name__)


class ImportBaseCommand(BaseCommand, ABC):
    def add_arguments(self, parser):
        parser.add_argument("--body", help="The oparl id of the body")
        parser.add_argument(
            "--ignore-modified", dest="ignore_modified", action="store_true"
        )
        parser.add_argument("--force-singlethread", action="store_true")
        parser.add_argument(
            "--skip-download",
            action="store_true",
            dest="skip_download",
            default=False,
            help="Do not download and parse the files",
        )

    def get_importer(self, options: Dict[str, Any]) -> Tuple[Importer, Body]:
        if options.get("body"):
            body = Body.objects.get(oparl_id=options["body"])
        else:
            body = Body.objects.get(id=settings.SITE_DEFAULT_BODY)

        if body.oparl_id is not None:
            loader = get_loader_from_body(body.oparl_id)
            importer = Importer(
                loader, body, ignore_modified=options["ignore_modified"]
            )
        else:
            importer = Importer(
                BaseLoader(dict()), ignore_modified=options["ignore_modified"]
            )
        importer.force_singlethread = options["force_singlethread"]
        importer.download_files = not options["skip_download"]

        return importer, body
