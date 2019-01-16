from importer.management.commands._import_base_command import ImportBaseCommand
from importer.models import CachedObject


class Command(ImportBaseCommand):
    help = "Load the data from the oparl api"

    def handle(self, *args, **options):
        importer, body = self.get_importer(options)
        body_data = CachedObject.objects.get(url=body.oparl_id)
        importer.fetch_lists_initial([body_data.data])
