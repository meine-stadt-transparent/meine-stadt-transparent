import logging

from django.core.management.base import BaseCommand

from mainapp.functions.document_parsing import cleanup_extracted_text
from mainapp.models import File

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Fixes the parsed_text"

    def handle(self, *args, **options):
        files = File.objects.all()
        for file in files:
            if file.parsed_text:
                file.parsed_text = cleanup_extracted_text(file.parsed_text)
                file.save()
