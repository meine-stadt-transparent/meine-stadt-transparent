import json
import logging
import time
from pathlib import Path

from django.core.management import BaseCommand

from importer.json_datatypes import RisData

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    def handle(self, *args, **options):
        input_file: Path = Path("../scrape-session/out/json/Karlsruhe.json")

        with input_file.open() as fp:
            data = json.load(fp)
        start = time.time()
        ris_data: RisData = RisData.from_dict(data)
        end = time.time()
        print(end - start, type(ris_data))
