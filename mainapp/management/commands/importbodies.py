from importer.get_importer import get_importer
from .importoparl import Command as ImportOParlCommand


class Command(ImportOParlCommand):
    help = "Import the bodies from an oparl api into the database"

    def handle(self, *args, **options):
        importer = get_importer(options)
        bodies = importer.get_bodies()
        importer.bodies(bodies)
