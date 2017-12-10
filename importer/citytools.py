import json
import os
import subprocess

import requests

from mainapp.models import Body, SearchStreet, Location
import logging

overpass_api = 'http://overpass-api.de/api/interpreter'

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
    logger.info('Importing streets from {}'.format(gemeindeschluessel))

    query = streets_query_template.format(gemeindeschluessel)

    r = requests.post(overpass_api, data={'data': query})

    for node in r.json()['elements']:
        if node['type'] == 'way':
            obj = SearchStreet.objects.filter(osm_id=node['id'])
            if obj.count() == 0:
                street = SearchStreet()
                street.displayed_name = node['tags']['name']
                street.osm_id = node['id']
                street.save()

                street.bodies.add(body)

                logger.info("Created: %s" % node['tags']['name'])


def import_outline(body, gemeindeschluessel, tmpfile):
    if not body.outline:
        outline = Location()
        outline.name = 'Outline of ' + body.name
        outline.short_name = body.short_name
        outline.is_official = False
    else:
        outline = body.outline

    logger.info("Importing outline from {}".format(gemeindeschluessel))

    query = query_template_outline.format(gemeindeschluessel)

    r = requests.post(overpass_api, data={'data': query})

    geojson = convert_to_geojson(r.text, tmpfile)
    outline.geometry = geojson
    outline.save()

    body.outline = outline
    body.save()


def convert_to_geojson(osm, tmpfile):
    with open(tmpfile, 'w') as file:
        file.write(osm)

    result = subprocess.run(['node_modules/.bin/osmtogeojson', '-f', 'json', '-m', tmpfile], stdout=subprocess.PIPE)
    geojson = json.loads(result.stdout.decode('utf-8'))

    os.remove(tmpfile)

    return geojson
