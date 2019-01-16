from importer.management.commands._import_base_command import ImportBaseCommand


class Command(ImportBaseCommand):
    help = "Try to resume an aborted import"

    def handle(self, *args, **options):
        importer, _body = self.get_importer(options)
        importer.import_objects()
