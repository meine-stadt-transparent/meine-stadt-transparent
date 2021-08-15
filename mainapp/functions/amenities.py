import logging

import requests

from mainapp.models import SearchPoi

logger = logging.getLogger(__name__)

query_template = """
[out:json];area["de:amtlicher_gemeindeschluessel"~"^{}"];
foreach(
    rel(pivot)->.a;
    .a out meta;
    (node(area)[amenity={}][name];>;);
    out qt meta;
);
"""
overpass = "http://overpass-api.de/api/interpreter"


def import_amenities(body, ags, amenity):
    query = query_template.format(ags, amenity)

    response = requests.post(overpass, data={"data": query})
    response.raise_for_status()
    for node in response.json()["elements"]:
        if node["type"] == "node":
            obj = SearchPoi.objects.filter(osm_id=node["id"])
            if obj.count() == 0:
                poi = SearchPoi()
                poi.displayed_name = node["tags"]["name"]
                poi.osm_id = node["id"]
                poi.osm_amenity = amenity
                poi.geometry = {
                    "type": "Point",
                    "coordinates": [node["lon"], node["lat"]],
                }
                poi.save()

                poi.body = body
                logger.info("Created: %s" % node["tags"]["name"])
