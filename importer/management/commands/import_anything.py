import logging

from importer.management.commands._import_base_command import ImportBaseCommand

logger = logging.getLogger(__name__)


class Command(ImportBaseCommand):
    help = "Import any oparl object by its id"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("id", help="The id of the object")
        parser.add_argument("--update", action="store_true")

    def handle(self, *args, **options):
        importer, _body = self.get_importer(options)

        importer.converter.import_anything(options["id"], options["update"]).save()
