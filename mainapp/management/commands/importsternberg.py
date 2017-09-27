from .importoparl import Command as OParlImport


class Command(OParlImport):
    help = 'Import the data from an oparl api into '

    def handle(self, *args, **options):
        # Remove gi requirement for running tests
        try:
            from importer.sternberg_import import SternbergImport
        except ImportError as e:
            if str(e) == "No module named 'gi'":
                self.stderr.write("You need to install liboparl for the importer. The readme contains the installation "
                                  "instructions")
                return
            else:
                raise e
        SternbergImport(
            options['entrypoint'],
            options['cachefolder'],
            options["storagefolder"],
            options["download_files"],
            options["threadcount"]
        ).run()
