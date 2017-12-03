import os
from django.core.management.base import BaseCommand

from mainapp.functions.document_parsing import get_page_count_from_pdf
from mainapp.models import File


class Command(BaseCommand):
    help = 'Imports streets from OpenStreetMap for a given city (amtlicher_gemeindeschluessel=gemeideschlüssel)'

    def handle(self, *args, **options):
        files = File.objects.all()
        for file in files:
            if file.storage_filename and file.mime_type == "application/pdf":
                path = os.path.join("../mst-storage/files", file.storage_filename)
                page_count = get_page_count_from_pdf(path)
                print(path + ": " + page_count)
                file.page_count = page_count
                file.save()
