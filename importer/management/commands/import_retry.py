from importer.management.commands._import_base_command import ImportBaseCommand


class Command(ImportBaseCommand):
    help = "Try to resume an aborted import"

    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument("--no-update", action="store_true")

    def handle(self, *args, **options):
        importer, _body = self.get_importer(options)
        importer.import_bodies(update=not options["no_update"])
        importer.import_objects(update=not options["no_update"])
