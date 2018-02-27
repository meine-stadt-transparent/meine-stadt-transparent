from importer.functions import get_importer
from .importoparl import Command as ImportOParlCommand


class Command(ImportOParlCommand):
    help = 'Import the bodies from an oparl api into the database'

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument('list', choices=["paper", "person", "organization", "meeting"])
        parser.add_argument('--cutoff', type=int)

    def get_with_cutoff(self, fn, cutoff):
        if cutoff:
            return lambda: fn()[:cutoff]
        else:
            return lambda: fn()

    def handle(self, *args, **options):
        importer = get_importer(options)(options)
        cutoff = options["cutoff"]

        bodies = importer.get_bodies()
        for body in bodies:
            if options["list"] == "paper":
                importer.list_batched(self.get_with_cutoff(body.get_paper, cutoff), importer.paper)
            elif options["list"] == "person":
                importer.list_batched(self.get_with_cutoff(body.get_person, cutoff), importer.person)
            elif options["list"] == "organization":
                importer.list_batched(self.get_with_cutoff(body.get_organization, cutoff), importer.organization)
            elif options["list"] == "meeting":
                importer.list_batched(self.get_with_cutoff(body.get_meeting, cutoff), importer.meeting)
            else:
                raise ValueError("Invalid list " + options["list"])
            importer.add_missing_associations()
