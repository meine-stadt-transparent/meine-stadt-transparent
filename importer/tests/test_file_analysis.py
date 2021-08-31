import os
from typing import Optional, Dict, Any
from unittest import mock

import pytest
from django.test import TestCase, override_settings

from importer.importer import Importer
from importer.loader import BaseLoader
from importer.tests.utils import MockLoader
from mainapp.functions.document_parsing import AddressPipeline
from mainapp.models import Body, File
from mainapp.tests.utils import MinioMock

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


class MockImporter(Importer):
    # noinspection PyMissingConstructor
    def __init__(self, *args, **kwargs):
        pass

    def download_and_analyze_file(
        self, file_id: int, address_pipeline: AddressPipeline, fallback_city: str
    ) -> bool:
        """Just allocates some MB for file 1"""
        if file_id == 1:
            # print is just to avoid possible optimizations
            print([[1 for _ in range(1024)] for _ in range(1024)])
        return True


@pytest.mark.skip(reason="flaky")
@pytest.mark.skipif(
    os.environ.get("CI") == "true",
    reason="Github actions seems to not respect the memory limit",
)
def test_load_file_oom(caplog):
    importer = MockImporter(BaseLoader({}), force_singlethread=True)

    with override_settings(SUBPROCESS_MAX_RAM=1 * 1024 * 1024):
        failed = importer.load_files_multiprocessing(
            AddressPipeline([]), "München", list(range(64))
        )
        assert failed == 1
        assert caplog.messages == [
            "File 1: Import failed du to excessive memory usage (Limit: 1048576)"
        ]
