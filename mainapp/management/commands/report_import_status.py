import inspect
import logging

from django.core.management.base import BaseCommand
from django.db.models import Count
from django.db.models import Model

from mainapp import models
from mainapp.models import File, Body

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
