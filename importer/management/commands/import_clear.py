import logging

from django.core.management.base import BaseCommand

from importer.functions import clear_import

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Clear all data from the oparl api identified by the prefix"

    def add_arguments(self, parser):
        parser.add_argument("prefix")
        parser.add_argument("--skip-cache", action="store_true")

    def handle(self, *args, **options):
        clear_import(options["prefix"], not options["skip_cache"])
