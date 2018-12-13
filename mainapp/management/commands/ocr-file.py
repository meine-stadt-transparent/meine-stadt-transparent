import logging

import os

from django.conf import settings
from django.core.management.base import BaseCommand
from django.db.models import Q

from mainapp.functions.document_parsing import (
    get_ocr_text_from_pdf,
    extract_persons,
    cleanup_extracted_text,
    extract_locations,
)
from mainapp.functions.minio import minio_client, minio_file_bucket
from mainapp.models import File


class Command(BaseCommand):
    help = "OCRs a file and writes the result back to the database"

    def add_arguments(self, parser):
        parser.add_argument("--id", type=int, help="OCR the file with the given ID")
        parser.add_argument(
            "--empty",
            dest="all_empty",
            action="store_true",
            help="OCR all files with empty parsed_text",
        )

    def parse_file(self, file: File):
        logging.info("- Parsing: " + str(file.id) + " (" + file.name + ")")
        with minio_client.get_object(minio_file_bucket, str(file.id)) as file_handle:
            recognized_text = get_ocr_text_from_pdf(file_handle.read())
        if len(recognized_text) > 0:
            file.parsed_text = cleanup_extracted_text(recognized_text)
            file.mentioned_persons = extract_persons(
                file.name + "\n" + (recognized_text or "") + "\n"
            )
            file.locations = extract_locations(recognized_text)
            file.save()
        else:
            logging.warning("Nothing recognized")

    def handle(self, *args, **options):
        if options["all_empty"]:
            all_files = File.objects.filter(
                Q(parsed_text="") | Q(parsed_text__isnull=True)
            ).all()
            for file in all_files:
                try:
                    self.parse_file(file)
                except Exception:
                    logging.error("Error parsing file: " + str(file.id))
        elif options["id"]:
            file = File.objects.get(id=options["id"])
            self.parse_file(file)
