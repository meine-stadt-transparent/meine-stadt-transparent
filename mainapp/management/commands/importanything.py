import re

from importer.get_importer import get_importer
from .importoparl import Command as ImportOParlCommand


class Command(ImportOParlCommand):
    help = "Import the bodies from an oparl api into the database"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("url", type=str)

    def handle(self, *args, **options):
        importer = get_importer(options)

        def convert(name):
            """ https://stackoverflow.com/a/1176023/3549270 """
            s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
            return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

        oparlobject = importer.utils.resolve(options["url"]).resolved_data
        oparltype = convert(oparlobject["type"].split("/")[-1])
        getattr(importer, oparltype)(oparlobject)
        importer.embedded.add_embedded_objects()
        importer.embedded.add_missing_associations()
