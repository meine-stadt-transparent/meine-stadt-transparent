import os
from typing import Optional, Dict, Any
from unittest import mock

from django.test import TestCase

from mainapp.functions.document_parsing import (
    extract_locations,
    extract_from_file,
    extract_persons,
)
from mainapp.models import File, Person
from mainapp.tests.main import test_media_root

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

    def test_pdf_parsing(self):
        file = os.path.join(
            test_media_root, "Donald Knuth - The Complexity of Songs.pdf"
        )
        with open(file, "rb") as fp:
            parsed_text, page_count = extract_from_file(fp, file, "application/pdf", 0)
        self.assertTrue("bottles of beer" in parsed_text)
        self.assertEqual(page_count, 3)
