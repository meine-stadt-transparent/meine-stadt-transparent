import json
from unittest import skip

import pytest
import responses
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


@pytest.mark.django_db
@pytest.mark.parametrize(
    "ags",
    [
        "09184119",  # Garching: eingemeindet
        "09162",  # München: Kreisfrei, kurz
        "09162000",  # München: Kreisfrei, lang
        "13076",  # Landkreis Ludwigslust-Parchim: Kreis, kurz
        "13076000",  # Landkreis Ludwigslust-Parchim: Kreis, lang
    ],
)
def test_import_outline(pytestconfig, ags):
    """This test exists mostly for the handling of the AGS with 5 vs. 8 digits"""
    # This currently assumes that we don't want to do any transformations with the ags before assigning it to the body
    body = Body(name=f"Place with AGS {ags}", short_name=f"AGS{ags}", ags=ags)
    with responses.RequestsMock() as requests_mock:
        fixture = pytestconfig.rootpath.joinpath(
            f"testdata/outline_query_responses/{ags}.json"
        )
        fixture = json.loads(fixture.read_text())
        requests_mock.add(
            method=responses.POST, url=fixture["url"], body=fixture["response"]
        )
        import_outline(body, ags)
