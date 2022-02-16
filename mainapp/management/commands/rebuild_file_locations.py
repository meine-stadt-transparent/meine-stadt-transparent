import logging

from django.conf import settings
from django.core.management.base import BaseCommand

from mainapp.functions.document_parsing import extract_locations
from mainapp.models import File, Body

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Rebuilds the file locations"

    def add_arguments(self, parser):
        parser.add_argument("--id", type=int, nargs="*", help="Rebuild only one file")
        parser.add_argument(
            "--all", dest="all", action="store_true", help="Rebuild all files"
        )

    def parse_file(self, file: File, fallback_city: str):
        self.stdout.write("Parsing: " + str(file.id) + " (" + file.name + ")")
        locations = extract_locations(file.parsed_text, fallback_city)
        self.stdout.write("{} locations found".format(len(locations)))
        file.locations.set(locations)
        file.save()

    def handle(self, *args, **options):
        fallback_city = (
            settings.GEOEXTRACT_SEARCH_CITY
            or Body.objects.get(id=settings.SITE_DEFAULT_BODY).short_name
        )

        if options["all"]:
            all_files = File.objects.all()
            for file in all_files:
                try:
                    self.parse_file(file, fallback_city)
                except Exception as e:
                    logger.exception(str(e))
                    self.stderr.write(
                        "Error parsing file: {}: {}".format(str(file.id), e)
                    )
        elif options["id"]:
            for file_id in options["id"]:
                file = File.objects.get(id=file_id)
                self.parse_file(file, fallback_city)
