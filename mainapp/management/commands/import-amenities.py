import requests
from django.core.management.base import BaseCommand

from mainapp.models import SearchPoi, Body


class Command(BaseCommand):
    help = 'Imports amenities from OpenStreetMap for a given city (amtlicher_gemeindeschluessel=gemeideschlüssel)'

    def add_arguments(self, parser):
        parser.add_argument('gemeindeschluessel', type=str)
        parser.add_argument('amenity', type=str)
        parser.add_argument('body-id', type=int)

    def handle(self, *args, **options):
        body = Body.objects.filter(id=options['body-id'])
        if body.count() == 0:
            self.stderr.write("Body not found: %s" % options['body-id'])
            return

        query = '[out:json];area["de:amtlicher_gemeindeschluessel"~"^%s"];\
            foreach(\
             rel(pivot)->.a;\
             .a out meta;\
             (node(area)[amenity=%s][name];>;);\
             out qt meta;\
            );' % (options['gemeindeschluessel'], options['amenity'])

        r = requests.post('http://overpass-api.de/api/interpreter', data={'data': query})

        for node in r.json()['elements']:
            if node['type'] == 'node':
                obj = SearchPoi.objects.filter(osm_id=node['id'])
                if obj.count() == 0:
                    poi = SearchPoi()
                    poi.displayed_name = node['tags']['name']
                    poi.osm_id = node['id']
                    poi.osm_amenity = options['amenity']
                    poi.geometry = {'type': 'Point', 'coordinates': [node['lon'], node['lat']]}
                    poi.save()

                    poi.bodies.add(body[0])
                    self.stdout.write("Created: %s" % node['tags']['name'])
