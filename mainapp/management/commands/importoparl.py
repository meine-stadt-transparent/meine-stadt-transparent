from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Import the data from an oparl api into the database'

    def add_arguments(self, parser, add_entrypoint=True):
        from importer.oparl_helper import default_options
        if add_entrypoint:
            parser.add_argument('entrypoint', type=str)
        parser.add_argument('--cachefolder', type=str)
        parser.add_argument('--storagefolder', type=str)
        parser.add_argument('--threadcount', type=int)
        parser.add_argument('--download-files', dest='download_files', action='store_true')
        parser.add_argument('--no-download-files', dest='download_files', action='store_false')
        parser.add_argument('--use-cache', dest='use_cache', action='store_true')
        parser.add_argument('--no-use-cache', dest='use_cache', action='store_false')
        parser.add_argument('--use-sternberg-workarounds', dest='use_sternberg', action='store_true')
        parser.add_argument('--ignore-modified', dest='ignore_modified', action='store_true')
        parser.add_argument('--no-threads', dest='no_threads', action='store_true', help="Debug option")
        parser.add_argument('--batchsize', type=int)
        parser.set_defaults(**default_options)

    # noinspection PyUnresolvedReferences
    @staticmethod
    def import_importer(options):
        # Remove gi requirement for running tests
        try:
            if options["use_sternberg"]:
                from importer.sternberg_import import SternbergImport as Importer
            else:
                from importer.oparl_import import OParlImport as Importer
        except ImportError as e:
            if str(e) == "No module named 'gi'":
                raise ImportError("You need to install liboparl for the importer. The readme contains the installation "
                                  "instructions")
            else:
                raise e

        return Importer

    def handle(self, *args, **options):
        importer = self.import_importer(options)(options)
        importer.run()
