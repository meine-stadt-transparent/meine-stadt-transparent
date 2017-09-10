from django.core.management.base import BaseCommand
from mainapp.functions.document_parsing import extract_file_geodata

import json


class Command(BaseCommand):
    help = 'Closes the specified poll for voting'

    def add_arguments(self, parser):
        parser.add_argument('file-id', type=int)

    def handle(self, *args, **options):
        found = extract_file_geodata(options['file-id'])
        print(json.dumps(found, indent=4, sort_keys=True))
