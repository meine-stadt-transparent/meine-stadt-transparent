import logging

from importer.management.commands._import_base_command import ImportBaseCommand
from importer.models import ExternalList, CachedObject

logger = logging.getLogger(__name__)


class Command(ImportBaseCommand):
    help = "Import the objects from an external list of an oparl body"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            "list", choices=["paper", "person", "organization", "meeting"]
        )

    def handle(self, *args, **options):
        importer, body = self.get_importer(options)
        body_data = CachedObject.objects.get(url=body.oparl_id)
        oparl_id = body_data.data[options["list"]]

        if ExternalList.objects.filter(url=oparl_id).exists():
            importer.fetch_list_update(oparl_id)
        else:
            importer.fetch_list_initial(oparl_id)

        importer.import_objects()
