import inspect
import logging

from django.contrib.auth.models import User
from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db.models import Model

from mainapp import models
from mainapp.functions.minio import minio_client, minio_file_bucket
from mainapp.models import File, Body, UserAlert

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Prints some statistics about the currently available data"

    def handle(self, *args, **options):
        for name, obj in inspect.getmembers(models):
            if (
                not inspect.isclass(obj)
                or not issubclass(obj, Model)
                or name in ["DefaultFields"]
            ):
                continue
            self.stdout.write(f"{name}: {obj.objects.count()}")
        files_total = File.objects.count()
        files_with_text = File.objects.filter(parsed_text__isnull=False).count()
        files_with_location = (
            File.objects.annotate(location_count=Count("locations"))
            .filter(location_count__gte=1)
            .count()
        )
        files_with_persons = (
            File.objects.annotate(persons_count=Count("mentioned_persons"))
            .filter(persons_count__gte=1)
            .count()
        )
        files_not_downloaded = File.objects.filter(
            filesize__isnull=True, oparl_access_url__isnull=False
        ).count()
        files_without_url = File.objects.filter(oparl_access_url__isnull=True).count()
        self.stdout.write(
            f"Files total: {files_total}; with text: {files_with_text}; "
            f"with locations: {files_with_location}; with persons: {files_with_persons}; "
            f"not downloaded: {files_not_downloaded}; without url: {files_without_url}"
        )
        bodies_with_outline = Body.objects.filter(outline__isnull=False).count()
        bodies_with_ags = Body.objects.filter(ags__isnull=False).count()
        self.stdout.write(
            f"Bodies with an outline: {bodies_with_outline}; with an ags: {bodies_with_ags}"
        )

        users_with_alerts = UserAlert.objects.values("user").distinct().count()
        users = User.objects.count()
        alerts = UserAlert.objects.count()
        self.stdout.write(
            f"There are {alerts} alerts by {users_with_alerts} of {users} users"
        )

        # Check if there are files which are listed as imported but aren't in minio
        # We convert everything to strings because there might be non-numeric files in minio
        existing_files = set(
            file.object_name for file in minio_client().list_objects(minio_file_bucket)
        )
        expected_files = set(
            str(i)
            for i in File.objects.filter(filesize__gt=0).values_list("id", flat=True)
        )
        missing_files = len(expected_files - existing_files)
        if missing_files > 0:
            self.stdout.write(
                f"{missing_files} files are marked as imported but aren't available in minio"
            )
