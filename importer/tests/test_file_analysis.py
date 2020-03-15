# In[]
from typing import Optional, Dict, Any
from unittest import mock

from django.test import TestCase

from importer.importer import Importer
from importer.tests.utils import MockLoader
from mainapp.models import Body, File
from mainapp.tests.main import MinioMock

download_url = "https://oparl.example.org/download/0"

filename = "testdata/media/Donald Knuth - The Complexity of Songs.pdf"

marina_trench = [142.2, 11.35]


def geocode(search_str: str) -> Optional[Dict[str, Any]]:
    if search_str == "There's a Hole in the Bottom of the Sea, München, Deutschland":
        return {"type": "Point", "coordinates": marina_trench}
    raise AssertionError(search_str)


class TestFileAnalysis(TestCase):
    fixtures = ["file-analysis"]

    @mock.patch("mainapp.functions.document_parsing.geocode", new=geocode)
    @mock.patch("mainapp.functions.minio._minio_singleton", new=MinioMock())
    def test_file_analysis(self):
        loader = MockLoader()
        with open(filename, "rb") as fp:
            loader.files[download_url] = (fp.read(), "application/pdf")

        importer = Importer(loader, force_singlethread=True)

        [body] = Body.objects.all()

        importer.load_files(fallback_city=body.short_name)

        [file] = File.objects.all()

        self.assertEqual(file.mime_type, "application/pdf")
        self.assertEqual(file.page_count, 3)
        self.assertEqual(len(file.parsed_text), 10019)
        self.assertEqual(file.coordinates(), [{"lat": 11.35, "lon": 142.2}])
        self.assertEqual(file.person_ids(), [1])
