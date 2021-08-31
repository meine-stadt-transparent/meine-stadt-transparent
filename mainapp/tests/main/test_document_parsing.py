from typing import Optional, Dict, Any
from unittest import mock

import pytest
from django.test import TestCase
from django.test import override_settings

from mainapp.functions.document_parsing import (
    extract_locations,
    extract_from_file,
    extract_persons,
)
from mainapp.models import File, Person
from mainapp.tests.utils import test_media_root

values = {
    "Tel-Aviv-Straße, Köln, Deutschland": {"lng": 6.9541377, "lat": 50.9315404},
    "Ankerstraße, Köln, Deutschland": {"lng": 6.9549345, "lat": 50.9281171},
    "Severinstraße, Köln, Deutschland": {"lng": 6.9564307, "lat": 50.9311172},
    "Tel-Aviv-Straße 12, Köln, Deutschland": {"lng": 6.955077, "lat": 50.9301069},
    "Karlstraße 7, 76133 Karlsruhe, Deutschland": {"lng": 8.3954236, "lat": 49.0113785},
    "Friedenstraße 10, 80689 München, Deutschland": {"lng": 11.4895, "lat": 48.1291},
}


def geocode(search_str: str) -> Optional[Dict[str, Any]]:
    for address, coordinates in values.items():
        if address.startswith(search_str):
            return {
                "type": "Point",
                "coordinates": [coordinates["lng"], coordinates["lat"]],
            }
    return None


class TestDocumentParsing(TestCase):
    fixtures = ["initdata", "cologne-pois-test"]

    @mock.patch("mainapp.functions.document_parsing.geocode", new=geocode)
    def test_location_extraction(self):
        file = File.objects.get(id=3)
        locations = extract_locations(file.parsed_text, "Köln")
        location_names = []
        for location in locations:
            location_names.append(location.description)

        self.assertTrue("Tel-Aviv-Straße" in location_names)
        self.assertTrue("Tel-Aviv-Straße 12" in location_names)
        self.assertTrue("Karlstraße 7" in location_names)
        self.assertFalse("Wolfsweg" in location_names)

    def test_person_extraction(self):
        frank = Person.objects.get(pk=1)
        doug = Person.objects.get(pk=4)
        will = Person.objects.get(pk=7)

        text = "A text \nabout Frank Underwood, Stamper, Doug, and a \nmisspelled WilliamConway."
        persons = extract_persons(text)
        self.assertTrue(doug in persons)
        self.assertTrue(frank in persons)
        self.assertTrue(will not in persons)

        text = 'Also the more formal name, "Underwood, Francis" should be found.'
        persons = extract_persons(text)
        self.assertTrue(doug not in persons)
        self.assertTrue(frank in persons)
        self.assertTrue(will not in persons)

        text = "We should check word boundaries like Doug Stampering something."
        persons = extract_persons(text)
        self.assertTrue(doug not in persons)


def test_pdf_parsing(pytestconfig, caplog):
    file = pytestconfig.rootpath.joinpath(test_media_root).joinpath(
        "Donald Knuth - The Complexity of Songs.pdf"
    )

    with file.open("rb") as fp:
        parsed_text, page_count = extract_from_file(fp, file, "application/pdf", 0)
    assert caplog.messages == []
    assert "bottles of beer" in parsed_text
    assert page_count == 3


@override_settings(SUBPROCESS_MAX_RAM=1 * 1024 * 1024)
def test_pdf_parsing_oom(pytestconfig, caplog):
    """Check error handling when pdftotext tries to use more than the allowed memory"""
    file = pytestconfig.rootpath.joinpath(test_media_root).joinpath(
        "Donald Knuth - The Complexity of Songs.pdf"
    )

    with file.open("rb") as fp:
        parsed_text, page_count = extract_from_file(fp, file, "application/pdf", 0)
    assert caplog.messages == [
        "File 0: Failed to run pdftotext: Command '['pdftotext', "
        f"PosixPath('{file}'), '-']' returned non-zero exit status 127."
    ]
    assert parsed_text is None
    assert page_count == 3


@pytest.mark.parametrize("filename", ["sample.tiff", "table.xls", "table.ods"])
def test_pdf_as_tiff(pytestconfig, caplog, filename):
    """A tiff tagged as pdf, making PyPDF2 fail

    https://github.com/codeformuenster/kubernetes-deployment/pull/65#issuecomment-894232803"""
    file = pytestconfig.rootpath.joinpath("testdata/media").joinpath(filename)
    with file.open("rb") as fp:
        parsed_text, page_count = extract_from_file(fp, file, "application/pdf", 0)
    assert caplog.messages == [
        "File 0: Failed to run pdftotext: Command '['pdftotext', "
        f"PosixPath('{file}'), '-']' returned non-zero exit status 1.",
        "File 0: Pdf does not allow to read the number of pages",
    ]
    assert not parsed_text
    assert not page_count
