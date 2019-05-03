from unittest import skip

from django.test import TestCase

from mainapp.functions.citytools import import_outline, import_streets
from mainapp.models import Body, SearchStreet


@skip
class TestCitytools(TestCase):
    fixtures = ["initdata"]
    ags_munich = "09162000"
    ags_tiny_city_called_bruecktal = "07233208"

    def test_import_outline(self):
        body = Body.objects.get(id=1)
        import_outline(body, self.ags_munich)
        self.assertEqual(
            len(body.outline.geometry["features"][0]["geometry"]["coordinates"][0][0]),
            10,
        )

    def test_import_streets(self):
        body = Body.objects.get(id=1)
        import_streets(body, self.ags_tiny_city_called_bruecktal)
        self.assertEqual(SearchStreet.objects.count(), 9)
