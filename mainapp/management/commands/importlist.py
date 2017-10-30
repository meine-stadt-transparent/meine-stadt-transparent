import re

from .importoparl import Command as ImportOParlCommand


class Command(ImportOParlCommand):
    help = 'Import the bodies from an oparl api into the database'

    def add_arguments(self, parser, add_entrypoint=True):
        super().add_arguments(parser, add_entrypoint)
        parser.add_argument('list', choices=["paper", "person", "organization", "meeting"])

    def handle(self, *args, **options):
        importer = self.import_importer(options)
        importer = importer(options)

        bodies = importer.get_bodies()
        for body in bodies:
            if options["list"] == "paper":
                importer.list_batched(body.get_paper, importer.paper)
            elif options["list"] == "person":
                importer.list_batched(body.get_person, importer.person)
            elif options["list"] == "organization":
                importer.list_batched(body.get_organization, importer.organization)
            elif options["list"] == "meeting":
                importer.list_batched(body.get_meeting, importer.meeting)
            else:
                raise ValueError("Invalid list " + options["list"])
