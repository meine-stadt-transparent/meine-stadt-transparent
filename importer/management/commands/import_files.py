import logging

from importer.management.commands._import_base_command import ImportBaseCommand
from mainapp.functions.document_parsing import AddressPipeline, create_geoextract_data
from meine_stadt_transparent import settings

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

    def handle(self, *args, **options):
        importer, body = self.get_importer(options)
        fallback_city = settings.GEOEXTRACT_SEARCH_CITY or body.short_name
        logger.info(f"Using '{fallback_city}' as geotagging city")
        if options["ids"]:
            address_pipeline = AddressPipeline(create_geoextract_data())
            failed = 0
            for file in options["ids"]:
                succeeded = importer.download_and_analyze_file(
                    file, address_pipeline, fallback_city=fallback_city
                )

                if not succeeded:
                    failed += 1

            if failed > 0:
                logger.error(f"{failed} files failed to download")
        else:
            importer.load_files(
                max_workers=options["max_workers"], fallback_city=fallback_city
            )
