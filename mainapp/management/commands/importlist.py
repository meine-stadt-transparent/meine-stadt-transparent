from importer.get_importer import get_importer
from .importoparl import Command as ImportOParlCommand


class Command(ImportOParlCommand):
    help = "Import the bodies from an oparl api into the database"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("body", help="The url of the body")
        parser.add_argument(
            "list", choices=["paper", "person", "organization", "meeting"]
        )

    def handle(self, *args, **options):
        importer = get_importer(options)

        body = importer.utils.resolve(options["body"]).resolved_data
        if options["list"] == "paper":
            importer.process_list(body["paper"], importer.paper)
        elif options["list"] == "person":
            importer.process_list(body["person"], importer.person)
        elif options["list"] == "organization":
            importer.process_list(body["organization"], importer.organization)
        elif options["list"] == "meeting":
            importer.process_list(body["meeting"], importer.meeting)
        else:
            raise ValueError("Invalid list " + options["list"])
        importer.embedded.add_embedded_objects()
        importer.embedded.add_missing_associations()
