import logging

from importer.functions import import_update
from importer.management.commands._import_base_command import ImportBaseCommand

logger = logging.getLogger(__name__)


class Command(ImportBaseCommand):
    help = """Update the data from an already imported oparl api.

    Uses all imported bodies with an oparl id unless `--body` is specified.
    """

    def handle(self, *args, **options):
        import_update(
            options["body"],
            ignore_modified=options["ignore_modified"],
            download_files=not options["skip_download"],
        )
