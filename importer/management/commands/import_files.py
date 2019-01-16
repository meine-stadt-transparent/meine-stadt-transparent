from importer.management.commands._import_base_command import ImportBaseCommand
from mainapp.functions.document_parsing import AddressPipeline, create_geoextract_data


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
        if options["ids"]:
            address_pipeline = AddressPipeline(create_geoextract_data())
            for file in options["ids"]:
                importer.download_and_analyze_file(
                    file, address_pipeline, body.short_name
                )
        else:
            importer.load_files(
                max_workers=options["max_workers"], fallback_city=body.short_name
            )
