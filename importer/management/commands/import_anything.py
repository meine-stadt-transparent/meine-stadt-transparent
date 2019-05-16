import logging

from importer.management.commands._import_base_command import ImportBaseCommand

logger = logging.getLogger(__name__)


class Command(ImportBaseCommand):
    help = "Import any oparl object by its id"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("ids", nargs="+", help="The oparl ids of the objects")

    def handle(self, *args, **options):
        importer, _body = self.get_importer(options)
        for oparl_id in options["ids"]:
            importer.import_anything(oparl_id).save()
