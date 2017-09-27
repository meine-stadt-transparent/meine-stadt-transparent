from collections import namedtuple
from unittest import mock

from django.test import TestCase, override_settings
from geopy import OpenCage

from mainapp.functions.document_parsing import extract_locations
from mainapp.models import File

values = {
    "Tel-Aviv-Straße, Köln, Deutschland": {'longitude': 6.9541377, 'latitude': 50.9315404},
    "Ankerstraße, Köln, Deutschland": {'longitude': 6.9549345, 'latitude': 50.9281171},
    "Severinstraße, Köln, Deutschland": {'longitude': 6.9564307, 'latitude': 50.9311172},
    "Tel-Aviv-Straße 12, Köln, Deutschland": {'longitude': 6.955077, 'latitude': 50.9301069},
    "Karlstraße 7, 76133 Karlsruhe, Deutschland": {'longitude': 8.3954236, 'latitude': 49.0113785},
    "Friedenstraße 10, 80689 München, Deutschland": {'longitude': 11.4895, 'latitude': 48.1291},
}


def geocode_mock(self, search_str, language, exactly_one):
    ResponseMock = namedtuple('ResponseMock', 'latitude longitude')
    for key, value in values.items():
        if key.startswith(search_str):
            return [ResponseMock(**value)]
    return None


@override_settings(ELASTICSEARCH_DSL_AUTOSYNC=False, ELASTICSEARCH_DSL_AUTO_REFRESH=False)
class TestDocumentParsing(TestCase):
    fixtures = ['initdata', 'cologne-pois-test']

    @mock.patch.object(OpenCage, 'geocode', new=geocode_mock)
    def test_extraction(self):
        file = File.objects.get(id=3)
        locations = extract_locations(file.parsed_text, 'Köln')
        location_names = []
        for location in locations:
            location_names.append(location.name)

        self.assertTrue('Tel-Aviv-Straße' in location_names)
        self.assertTrue('Tel-Aviv-Straße 12' in location_names)
        self.assertTrue('Karlstraße 7' in location_names)
        self.assertFalse('Wolfsweg' in location_names)
