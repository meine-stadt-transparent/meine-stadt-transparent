import logging

from importer.management.commands._import_base_command import ImportBaseCommand
from importer.models import CachedObject

logger = logging.getLogger(__name__)


class Command(ImportBaseCommand):
    help = "Load the data from the oparl api"

    def handle(self, *args, **options):
        importer, body = self.get_importer(options)
        body_data = CachedObject.objects.get(url=body.oparl_id)
        importer.fetch_lists_initial([body_data.data])
        logger.info("You can now import the data with `./manage.py import_objects`")
