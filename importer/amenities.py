import logging

import requests

from mainapp.models import SearchPoi

logger = logging.getLogger(__name__)


class Importamenities:
    query_template = """
    [out:json];area["de:amtlicher_gemeindeschluessel"~"^{}"];
    foreach(
        rel(pivot)->.a;
        .a out meta;
        (node(area)[amenity={}][name];>;);
        out qt meta;
    );
    """
    overpass = 'http://overpass-api.de/api/interpreter'

    @classmethod
    def importamenities(cls, body, ags, amenity):
        query = cls.query_template.format(ags, amenity)

        r = requests.post(cls.overpass, data={'data': query})
        for node in r.json()['elements']:
            if node['type'] == 'node':
                obj = SearchPoi.objects.filter(osm_id=node['id'])
                if obj.count() == 0:
                    poi = SearchPoi()
                    poi.displayed_name = node['tags']['name']
                    poi.osm_id = node['id']
                    poi.osm_amenity = amenity
                    poi.geometry = {'type': 'Point', 'coordinates': [node['lon'], node['lat']]}
                    poi.save()

                    poi.bodies.add(body)
                    logger.info("Created: %s" % node['tags']['name'])
