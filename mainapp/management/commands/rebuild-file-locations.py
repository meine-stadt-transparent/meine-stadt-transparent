import logging

from django.core.management.base import BaseCommand

from mainapp.functions.document_parsing import extract_locations
from mainapp.models import File


class Command(BaseCommand):
    help = "Rebuilds the file locations"

    def add_arguments(self, parser):
        parser.add_argument("--id", type=int, help="Rebuild only one file")
        parser.add_argument(
            "--all", dest="all", action="store_true", help="Rebuild all files"
        )

    def parse_file(self, file: File):
        logging.info("- Parsing: " + str(file.id) + " (" + file.name + ")")
        file.locations = extract_locations(file.parsed_text)
        file.save()

    def handle(self, *args, **options):
        if options["all"]:
            all_files = File.objects.all()
            for file in all_files:
                try:
                    self.parse_file(file)
                except Exception:
                    logging.error("Error parsing file: " + str(file.id))
        elif options["id"]:
            file = File.objects.get(id=options["id"])
            self.parse_file(file)
