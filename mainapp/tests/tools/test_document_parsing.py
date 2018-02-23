import os
from collections import namedtuple
from unittest import mock

from django.conf import settings
from django.test import TestCase

from mainapp.functions.document_parsing import extract_locations, extract_text_from_pdf, \
    get_page_count_from_pdf, extract_persons
from mainapp.models import File, Person

values = {
    "Tel-Aviv-Straße, Köln, Deutschland": {
        'longitude': 6.9541377,
        'latitude': 50.9315404
    },
    "Ankerstraße, Köln, Deutschland": {
        'longitude': 6.9549345,
        'latitude': 50.9281171
    },
    "Severinstraße, Köln, Deutschland": {
        'longitude': 6.9564307,
        'latitude': 50.9311172
    },
    "Tel-Aviv-Straße 12, Köln, Deutschland": {
        'longitude': 6.955077,
        'latitude': 50.9301069
    },
    "Karlstraße 7, 76133 Karlsruhe, Deutschland": {
        'longitude': 8.3954236,
        'latitude': 49.0113785
    },
    "Friedenstraße 10, 80689 München, Deutschland": {
        'longitude': 11.4895,
        'latitude': 48.1291
    },
}


# noinspection PyUnusedLocal
class GeocodeMock:
    def geocode(self, search_str, language, exactly_one):
        ResponseMock = namedtuple('ResponseMock', 'latitude longitude')
        for key, value in values.items():
            if key.startswith(search_str):
                return [ResponseMock(**value)]
        return None


class TestDocumentParsing(TestCase):
    fixtures = ['initdata', 'cologne-pois-test']

    @mock.patch('mainapp.functions.geo_functions.get_geolocator', return_value=GeocodeMock())
    def test_location_extraction(self, _):
        file = File.objects.get(id=3)
        locations = extract_locations(file.parsed_text, 'Köln')
        location_names = []
        for location in locations:
            location_names.append(location.description)

        self.assertTrue('Tel-Aviv-Straße' in location_names)
        self.assertTrue('Tel-Aviv-Straße 12' in location_names)
        self.assertTrue('Karlstraße 7' in location_names)
        self.assertFalse('Wolfsweg' in location_names)

    def test_person_extraction(self):
        frank = Person.objects.get(pk=1)
        doug = Person.objects.get(pk=4)
        will = Person.objects.get(pk=7)

        text = "A text \nabout Frank Underwood, Stamper, Doug, and a \nmisspelled WilliamConway."
        persons = extract_persons(text)
        self.assertTrue(doug in persons)
        self.assertTrue(frank in persons)
        self.assertFalse(will in persons)

        text = "Also the more formal name, \"Underwood, Francis\" should be found."
        persons = extract_persons(text)
        self.assertFalse(doug in persons)
        self.assertTrue(frank in persons)
        self.assertFalse(will in persons)

    def test_pdf_parsing(self):
        file = os.path.abspath(os.path.dirname(__name__))
        file = os.path.join(file, settings.MEDIA_ROOT, 'Donald Knuth - The Complexity of Songs.pdf')
        parsed_text = extract_text_from_pdf(file)
        self.assertTrue('bottles of beer' in parsed_text)

    def test_pdf_page_numbers(self):
        file = os.path.abspath(os.path.dirname(__name__))
        file = os.path.join(file, settings.MEDIA_ROOT, 'Donald Knuth - The Complexity of Songs.pdf')
        page_count = get_page_count_from_pdf(file)
        self.assertEqual(3, page_count)
