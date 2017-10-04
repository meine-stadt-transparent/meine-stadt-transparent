import sys
from multiprocessing import Pool

from .importoparl import Command as OParlImport


class Command(OParlImport):
    help = 'Import the data from an oparl api into '

    def add_arguments(self, parser, add_entrypoint=False):
        super().add_arguments(parser, add_entrypoint)
        parser.add_argument('urlfile', type=str, default="urls.txt")

    def handle(self, *args, **options):
        importer = self.import_importer(options)

        urls = open(options["urlfile"]).readlines()
        urls = [url.strip() for url in urls]

        options_per_process = []
        for url in urls:
            localeoptions = dict(options)
            localeoptions["entrypoint"] = url
            options_per_process.append(localeoptions)

        with Pool(len(options_per_process)) as executor:
            results = executor.map(importer.run_static, options_per_process)

        print("\nAll processes finished\n")

        for success, options in zip(results, options_per_process):
            if success:
                print("SUCCESS: {}".format(options["entrypoint"]))
            else:
                print("FAILED: {}".format(options["entrypoint"]))

        print("\nFinal results: {} successes and {} failures\n".format(results.count(True), results.count(False)))

        if results.count(False) > 0:
            sys.exit(1)
