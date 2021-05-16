from typing import Set

from django.core.management.base import BaseCommand

from mainapp.functions.minio import minio_client, minio_file_bucket
from mainapp.models import File


class Command(BaseCommand):
    help = "Marks files as missing in the database that are deleted in minio"

    def handle(self, *args, **options):
        existing_files = set(
            int(file.object_name)
            for file in minio_client().list_objects(minio_file_bucket)
        )
        expected_files: Set[int] = set(
            File.objects.filter(filesize__gt=0).values_list("id", flat=True)
        )
        missing_files = expected_files - existing_files
        if len(missing_files) > 0:
            self.stdout.write(
                f"{len(missing_files)} files are marked as imported but aren't available in minio"
            )
            File.objects.filter(id__in=missing_files).update(filesize=None)
