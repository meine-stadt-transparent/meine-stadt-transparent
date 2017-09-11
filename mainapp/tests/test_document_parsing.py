from django.test import TestCase, override_settings

from mainapp.functions.document_parsing import extract_locations
from mainapp.models import File


@override_settings(ELASTICSEARCH_DSL_AUTOSYNC=False, ELASTICSEARCH_DSL_AUTO_REFRESH=False)
class TestDocumentParsing(TestCase):
    fixtures = ['initdata', 'cologne-pois-test']

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
