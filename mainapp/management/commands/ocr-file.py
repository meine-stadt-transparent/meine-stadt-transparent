import logging

import os

from django.conf import settings
from django.core.management.base import BaseCommand

from mainapp.functions.document_parsing import get_ocr_text_from_pdf
from mainapp.models import File


class Command(BaseCommand):
    help = 'OCRs a file and writes the result back to the database'

    def add_arguments(self, parser):
        parser.add_argument('id', type=int, help="Parse only the file with the given ID")

    def handle(self, *args, **options):
        file = File.objects.get(id=options['id'])
        logging.info("- Parsing: " + str(file.id) + " (" + file.name + ")")
        file_path = os.path.abspath(os.path.dirname(__name__))
        file_path = os.path.join(file_path, settings.MEDIA_ROOT, file.storage_filename)
        print(file_path)
        recognized_text = get_ocr_text_from_pdf(file_path)
        if len(recognized_text) > 0:
            file.parsed_text = recognized_text
            file.save()
        else:
            logging.warning("Nothing recognized")
