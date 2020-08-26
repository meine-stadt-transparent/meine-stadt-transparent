import logging
from typing import Optional

import osm2geojson
import requests
from django.db import IntegrityError

from mainapp.models import SearchStreet, Location, Body

overpass_api = "http://overpass-api.de/api/interpreter"

logger = logging.getLogger(__name__)

streets_query_template = """
[out:json];area["de:amtlicher_gemeindeschluessel"~"^{}"];
foreach(
    rel(pivot)->.a;
    .a out meta;
    (way(area)[highway~"^residential$|^service$|^unclassified$|^track$|^footway$|^tertiary$|^path$|^secondary$|^primary$|^cycleway$|^trunk$|^living_street$|^road$|^pedestrian$|^construction$"][name];>;);
    out qt meta;
);
"""

query_template_outline = """
[out:json];area["de:amtlicher_gemeindeschluessel"~"^{}"]->.cityarea;
rel(pivot.cityarea);
out geom;
"""


def import_streets(body: Body, gemeindeschluessel: Optional[str] = None):
    gemeindeschluessel = gemeindeschluessel or body.ags
    assert gemeindeschluessel is not None

    logger.info("Importing streets from {}".format(gemeindeschluessel))

    query = streets_query_template.format(gemeindeschluessel)

    response = requests.post(overpass_api, data={"data": query})
    response.raise_for_status()
    elements = response.json()["elements"]
    ways = [node for node in elements if node["type"] == "way"]
    logger.info("Found {} streets".format(len(ways)))

    streets = []
    for way in ways:
        streets.append(
            SearchStreet(
                displayed_name=way["tags"]["name"], osm_id=way["id"], body=body
            )
        )

    try:
        SearchStreet.objects.bulk_create(streets)
    except IntegrityError:
        logger.warning(
            "The streets were already imported "
            "(This will be fixed with the django 2.2 update through ignore_conflicts=True)"
        )


def import_outline(body: Body, gemeindeschluessel: Optional[str] = None):
    gemeindeschluessel = gemeindeschluessel or body.ags
    assert gemeindeschluessel is not None

    logger.info("Importing outline from {}".format(gemeindeschluessel))

    if not body.outline:
        outline = Location()
        outline.name = "Outline of " + body.name
        outline.short_name = body.short_name
        outline.is_official = False
    else:
        outline = body.outline

    query = query_template_outline.format(gemeindeschluessel)

    response = requests.post(overpass_api, data={"data": query})
    response.raise_for_status()
    geojson = osm2geojson.json2geojson(response.text)
    outline.geometry = geojson
    outline.save()

    body.outline = outline
    body.save()
