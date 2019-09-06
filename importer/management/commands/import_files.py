import logging

from importer.importer import Importer
from importer.loader import BaseLoader
from importer.management.commands._import_base_command import ImportBaseCommand
from mainapp.functions.document_parsing import AddressPipeline, create_geoextract_data

logger = logging.getLogger(__name__)


class Command(ImportBaseCommand):
    help = "Try to resume an aborted import"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("--ids", nargs="*", help="Only import these ids")
        parser.add_argument(
            "--max-workers",
            type=int,
            help="Use only that many processes for the import",
        )
        parser.add_argument(
            "--mock-body", help="Don't try to determine the body from its oparl id"
        )

    def handle(self, *args, **options):
        if options["mock_body"]:
            importer = Importer(BaseLoader(dict()))
            body_short_name = options["mock_body"]
        else:
            importer, body = self.get_importer(options)
            body_short_name = body.short_name
        if options["ids"]:
            address_pipeline = AddressPipeline(create_geoextract_data())
            failed = 0
            for file in options["ids"]:
                succeeded = importer.download_and_analyze_file(
                    file, address_pipeline, body_short_name
                )

                if not succeeded:
                    failed += 1

            if failed > 0:
                logger.error("{} files failed to download".format(failed))
        else:
            importer.load_files(
                max_workers=options["max_workers"], fallback_city=body_short_name
            )
