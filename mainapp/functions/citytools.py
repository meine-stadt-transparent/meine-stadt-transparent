"""
This tries to import the outline and the streets. The Problem is that we have 3 distinct type of districts:

 * Städte/Gemeinden that are part of a Kreis: 8-digit AGS, last three digits not 000
 * Kreisfreie Städte: 8-digit AGS, last three digits 000
 * Landkreise: Not really an AGS, but a 5-digit Kreisschlüssel, which is the prefix to the AGS of its cities and municipalities

### A Stadt in a Landkreis:

rel["de:amtlicher_gemeindeschluessel"~"^09184119"]
   [admin_level=8]
   [type=boundary]
   [boundary=administrative];
out geom;

-> Returns the city's outline

### A Kreisfreie Stadt

rel["de:amtlicher_gemeindeschluessel"~"^09162"]
   [admin_level=8]
   [type=boundary]
   [boundary=administrative];
out geom;

-> No data

rel["de:amtlicher_gemeindeschluessel"~"^09162"]
   [admin_level=6]
   [type=boundary]
   [boundary=administrative];
out geom;

-> works

rel["de:amtlicher_gemeindeschluessel"~"^09162000"]
   [admin_level=6]
   [type=boundary]
   [boundary=administrative];
out geom;

-> works

### A Landkreis

rel["de:amtlicher_gemeindeschluessel"~"^13076"]
   [admin_level=8]
   [type=boundary]
   [boundary=administrative];
out geom;

-> Returns each part of the Kreis (undesirable)

rel["de:amtlicher_gemeindeschluessel"~"^13076"]
   [admin_level=6]
   [type=boundary]
   [boundary=administrative];
out geom;

-> works

rel["de:amtlicher_gemeindeschluessel"~"^13076000"]
   [admin_level=6]
   [type=boundary]
   [boundary=administrative];
out geom;

-> No data (bad)
"""

import logging
from typing import Optional

import osm2geojson
import requests
from django.db import IntegrityError

from mainapp.models import SearchStreet, Location, Body

overpass_api = "http://overpass-api.de/api/interpreter"

logger = logging.getLogger(__name__)

streets_query_template = """
[out:json];area["de:amtlicher_gemeindeschluessel"~"^{}"]
   [admin_level={}]
   [type=boundary]
   [boundary=administrative];
foreach(
    rel(pivot)->.a;
    .a out meta;
    (way(area)[highway~"^residential$|^service$|^unclassified$|^track$|^footway$|^tertiary$|^path$|^secondary$|^primary$|^cycleway$|^trunk$|^living_street$|^road$|^pedestrian$|^construction$"][name];>;);
    out qt meta;
);
"""

query_template_outline = """
[out:json];rel["de:amtlicher_gemeindeschluessel"~"^{}"]
   [admin_level={}]
   [type=boundary]
   [boundary=administrative];
out geom;
"""


def format_template(template: str, ags: str) -> str:
    """See comment at the top of the file"""
    if len(ags) == 8 and ags.endswith("000"):
        # Don't take no risk that we're having a Kreis and someone added a 000 to make it 8 digits
        ags = ags[:5]

    if len(ags) == 5:
        # Landkreis or Kreisfreie Stadt
        admin_level = 6
    else:
        # Gemeinde or Stadt
        admin_level = 8

    return template.format(ags, admin_level)


def import_streets(body: Body, ags: Optional[str] = None):
    ags = ags or body.ags
    assert ags is not None

    logger.info("Importing streets from {}".format(ags))

    query = format_template(streets_query_template, ags)

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


def import_outline(body: Body, ags: Optional[str] = None):
    ags = ags or body.ags
    assert ags is not None

    logger.info("Importing outline from {}".format(ags))

    if not body.outline:
        outline = Location()
        outline.name = "Outline of " + body.name
        outline.short_name = body.short_name
        outline.is_official = False
    else:
        outline = body.outline

    query = format_template(query_template_outline, ags)

    response = requests.post(overpass_api, data={"data": query})
    response.raise_for_status()
    geojson = osm2geojson.json2geojson(response.text)
    outline.geometry = geojson
    outline.save()

    body.outline = outline
    body.save()
