from django.test import TestCase, override_settings

from mainapp.functions.document_parsing import extract_locations
from mainapp.models import File


@override_settings(ELASTICSEARCH_DSL_AUTOSYNC=False, ELASTICSEARCH_DSL_AUTO_REFRESH=False)
class TestDocumentParsing(TestCase):
    fixtures = ['initdata', 'cologne-pois']

    def test_extraction(self):
        file = File.objects.get(id=3)
        locations = extract_locations(file.parsed_text, 'Köln')
        for location in locations:
            print(location)

        self.assertEqual(1, locations)
