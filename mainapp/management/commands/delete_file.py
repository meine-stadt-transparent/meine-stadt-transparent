"""
Manually delete a file from minio
"""
from django.core.management.base import BaseCommand

from mainapp.functions.minio import minio_client, minio_file_bucket


class Command(BaseCommand):
    help = "Manually delete a file from minio"

    def add_arguments(self, parser):
        parser.add_argument("id", type=int)

    def handle(self, *args, **options):
        minio_client().remove_object(minio_file_bucket, str(options["id"]))
