from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from mainapp.functions.minio import minio_client, minio_file_bucket


class Command(BaseCommand):
    help = "Upload the Knuth test pdf for file 1"

    def handle(self, *args, **options):
        pdf = (
            Path(settings.BASE_DIR)
            .joinpath("testdata")
            .joinpath("media")
            .joinpath("Donald Knuth - The Complexity of Songs.pdf")
        )
        minio_client().fput_object(minio_file_bucket, "1", pdf)
