import logging

from django.core.management import BaseCommand

from importer.importer import Importer
from importer.loader import get_loader_from_body
from importer.models import CachedObject
from mainapp.models import File, Paper, Consultation, AgendaItem, Body

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """
    Usage: a) Import Kall b) Run this c) Look at the timestamps
    """

    help = "For development only"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "--prefix", default="https://sdnetrim.kdvz-frechen.de/rim4550"
        )
        parser.add_argument("--force-singlethread", action="store_true")

    def handle(self, *args, **options):
        prefix = options["prefix"]

        body = Body.objects.get(oparl_id__startswith=prefix)
        loader = get_loader_from_body(body.oparl_id)
        importer = Importer(loader, body)
        importer.force_singlethread = options["force_singlethread"]

        import_plan = [File, Paper, Consultation, AgendaItem]

        for class_object in import_plan:
            name = class_object.__name__
            stats = class_object.objects.filter(oparl_id__startswith=prefix).delete()
            logger.info(f"{name}: {stats}")

            CachedObject.objects.filter(
                url__startswith=prefix, oparl_type=class_object.__name__
            ).update(to_import=True)

        for type_class in import_plan:
            importer.import_type(type_class)
