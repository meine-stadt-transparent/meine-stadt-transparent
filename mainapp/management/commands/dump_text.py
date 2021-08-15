"""
Quick and dirty solution to quickly dump out potentially gigabytes of text into a json file
"""
import json

from django.core.management.base import BaseCommand
from tqdm import tqdm

from mainapp.models import File


class Command(BaseCommand):
    help = "Dump all text extracted from the pdfs to a json file"

    def add_arguments(self, parser):
        parser.add_argument("target")

    def handle(self, *args, **options):
        with open(options["target"], "w") as fp:
            fp.write("{\n")
            total = File.objects.count()
            for i, file in tqdm(enumerate(File.objects.all()), total=total):
                fp.write(f'    "{file.id}": ')
                fp.write(json.dumps(file.parsed_text))
                if i < total - 1:
                    fp.write(",\n")
                else:
                    fp.write("\n")
            fp.write("}")
