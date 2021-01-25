"""
Manually delete a file from minio
"""
from django.core.management.base import BaseCommand

from mainapp.models import File


class Command(BaseCommand):
    help = "Manually delete a file so that it won't be reimported"

    def add_arguments(self, parser):
        parser.add_argument("id", type=int)

    def handle(self, *args, **options):
        File.objects.get(pk=options["id"]).manually_delete()
