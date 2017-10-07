from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Import the data from an oparl api into the database'

    def add_arguments(self, parser, add_entrypoint=True):
        if add_entrypoint:
            parser.add_argument('entrypoint', type=str)
        parser.add_argument('--cachefolder', type=str, default="./storage/import-oparl-cache")
        parser.add_argument('--storagefolder', type=str, default="./storage/files")
        parser.add_argument('--threadcount', type=int, default=10)
        parser.add_argument('--download-files', dest='download-files', action='store_true')
        parser.add_argument('--no-download-files', dest='download-files', action='store_false')
        parser.add_argument('--use-cache', dest='use-cache', action='store_true')
        parser.add_argument('--no-use-cache', dest='use-cache', action='store_false')
        parser.add_argument('--use-sternberg-workarounds', dest='use-sternberg', action='store_true')
        parser.add_argument('--without-persons', dest='with-persons', action='store_false')
        parser.add_argument('--without-papers', dest='with-papers', action='store_false')
        parser.add_argument('--without-organizations', dest='with-organizations', action='store_false')
        parser.add_argument('--without-meetings', dest='with-meetings', action='store_false')
        parser.set_defaults(download_files=True)
        parser.set_defaults(use_cache=True)
        parser.set_defaults(use_sternberg=False)
        parser.set_defaults(with_persons=True)
        parser.set_defaults(with_papers=True)
        parser.set_defaults(with_organizations=True)
        parser.set_defaults(with_meetings=True)

    @staticmethod
    def import_importer(options):
        # Remove gi requirement for running tests
        try:
            if options["use-sternberg"]:
                from importer.sternberg_import import SternbergImport as Importer
            else:
                from importer.oparl_importer import OParlImporter as Importer
        except ImportError as e:
            if str(e) == "No module named 'gi'":
                raise ImportError("You need to install liboparl for the importer. The readme contains the installation "
                                  "instructions")
            else:
                raise e

        return Importer

    def handle(self, *args, **options):
        importer = self.import_importer(options)
        importer(options).run()
