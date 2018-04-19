from importer.functions import get_importer
from .importoparl import Command as ImportOParlCommand


class Command(ImportOParlCommand):
    help = 'Import the bodies from an oparl api into the database'

    def handle(self, *args, **options):
        importer = get_importer(options)

        bodies = importer.get_bodies()
        if importer.no_threads:
            importer.bodies_singlethread(bodies)
        else:
            importer.bodies_multithread(bodies)
