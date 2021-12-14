from django.core.management.base import BaseCommand

from importer.models import CachedObject


class Command(BaseCommand):
    help = "Set that all fetched objects still need to be downloaded, so that you work after purging the mainapp"

    def handle(self, *args, **options):
        CachedObject.objects.filter(to_import=False).update(to_import=True)
