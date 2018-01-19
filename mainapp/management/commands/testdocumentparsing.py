import logging

from django.core.management.base import BaseCommand

from mainapp.functions.document_parsing import extract_locations
from mainapp.models import File


class Command(BaseCommand):
    help = 'TODO'

    def add_arguments(self, parser):
        parser.add_argument('file-id', type=int)

    def handle(self, *args, **options):
        file = File.objects.get(id=options['file-id'])
        logging.info(file.displayed_filename)
        file.locations = extract_locations(file.parsed_text)
        file.save()
