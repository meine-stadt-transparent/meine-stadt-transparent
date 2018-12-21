import json
import logging
import os
import subprocess
import tempfile

import requests

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


def import_streets(body, gemeindeschluessel):
    logger.info("Importing streets from {}".format(gemeindeschluessel))

    query = streets_query_template.format(gemeindeschluessel)

    response = requests.post(overpass_api, data={"data": query})

    elements = response.json()["elements"]
    ways = [node for node in elements if node["type"] == "way"]
    logger.info("Found {} streets".format(len(ways)))

    for way in ways:
        obj = SearchStreet.objects.filter(osm_id=way["id"]).first()
        if not obj:
            street = SearchStreet()
            street.displayed_name = way["tags"]["name"]
            street.osm_id = way["id"]
            street.save()

            street.bodies.add(body)

            logger.info("Created: %s" % way["tags"]["name"])


def import_outline(body: Body, gemeindeschluessel: str):
    if not body.outline:
        outline = Location()
        outline.name = "Outline of " + body.name
        outline.short_name = body.short_name
        outline.is_official = False
    else:
        outline = body.outline

    logger.info("Importing outline from {}".format(gemeindeschluessel))

    query = query_template_outline.format(gemeindeschluessel)

    response = requests.post(overpass_api, data={"data": query})

    geojson = convert_to_geojson(response.text)
    outline.geometry = geojson
    outline.save()

    body.outline = outline
    body.save()


def convert_to_geojson(osm):
    with tempfile.NamedTemporaryFile(delete=False, mode="w") as file:
        file.write(osm)
        filename = file.name

    result = subprocess.run(
        ["node_modules/.bin/osmtogeojson", "-f", "json", "-m", filename],
        stdout=subprocess.PIPE,
    )
    geojson = json.loads(result.stdout.decode())

    os.remove(filename)

    return geojson
