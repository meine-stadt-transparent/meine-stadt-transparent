from django.core.management.base import BaseCommand
from mainapp.functions.document_parsing import extract_file_locations

import json


class Command(BaseCommand):
    help = 'Closes the specified poll for voting'

    def add_arguments(self, parser):
        parser.add_argument('file-id', type=int)
        parser.add_argument('city', type=str)

    def handle(self, *args, **options):
        found = extract_file_locations(options['file-id'], options['city'])
        print(json.dumps(found, indent=4, sort_keys=True))
