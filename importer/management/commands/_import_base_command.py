import logging
from abc import ABC
from typing import Tuple

from django.conf import settings
from django.core.management.base import BaseCommand

from importer.importer import Importer
from importer.loader import get_loader_from_body
from mainapp.models import Body

logger = logging.getLogger(__name__)


class ImportBaseCommand(BaseCommand, ABC):
    def add_arguments(self, parser):
        parser.add_argument("--body", help="The oparl id of the body")
        parser.add_argument(
            "--ignore-modified", dest="ignore_modified", action="store_true"
        )
        parser.add_argument("--force-singlethread", action="store_true")

    def get_importer(self, options: dict) -> Tuple[Importer, Body]:
        if options.get("body"):
            body = Body.objects.get(oparl_id=options["body"])
        else:
            body = Body.objects.get(id=settings.SITE_DEFAULT_BODY)
        loader = get_loader_from_body(body.oparl_id)
        importer = Importer(loader, body, ignore_modified=options["ignore_modified"])
        importer.force_singlethread = options["force_singlethread"]

        return importer, body
