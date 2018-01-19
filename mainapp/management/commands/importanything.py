import re

from importer.functions import get_importer
from .importoparl import Command as ImportOParlCommand


class Command(ImportOParlCommand):
    help = 'Import the bodies from an oparl api into the database'

    def add_arguments(self, parser, add_entrypoint=True):
        super().add_arguments(parser, add_entrypoint)
        parser.add_argument('url', type=str)

    def handle(self, *args, **options):
        importer = get_importer(options)(options)

        def convert(name):
            """ https://stackoverflow.com/a/1176023/3549270 """
            s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
            return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

        oparlobject = importer.client.parse_url(options["url"])
        oparltype = convert(oparlobject.get_oparl_type().split("/")[-1])
        getattr(importer, oparltype)(oparlobject)
        importer.add_missing_associations()
