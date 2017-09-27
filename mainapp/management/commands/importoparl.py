from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Import the data from an oparl api into '

    def add_arguments(self, parser):
        parser.add_argument('entrypoint', type=str)
        parser.add_argument('--cachefolder', type=str, default="/tmp/import-oparl-cache")
        parser.add_argument('--storagefolder', type=str, default="./import-storage")
        parser.add_argument('--threadcount', type=int, default=10)
        parser.add_argument('--download-files', dest='download_files', action='store_true')
        parser.add_argument('--no-download-files', dest='download_files', action='store_false')
        parser.set_defaults(download_files=True)

    def handle(self, *args, **options):
        # Remove gi requirement for running tests
        try:
            from importer.oparl_importer import OParlImporter
        except ImportError as e:
            if str(e) == "No module named 'gi'":
                self.stderr.write("You need to install liboparl for the importer. The readme contains the installation "
                                  "instructions")
                return
            else:
                raise e
        OParlImporter(
            options['entrypoint'],
            options['cachefolder'],
            options["storagefolder"],
            options["download_files"],
            options["threadcount"]
        ).run()
