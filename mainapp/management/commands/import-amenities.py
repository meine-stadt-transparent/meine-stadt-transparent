import json

from django.core.management.base import BaseCommand
import requests

from mainapp.models import SearchPoi


class Command(BaseCommand):
    help = 'Closes the specified poll for voting'

    def add_arguments(self, parser):
        parser.add_argument('gemeindeschluessel', nargs=1, type=str)
        parser.add_argument('amenity', nargs=1, type=str)
        parser.add_argument('body-id', nargs=1, type=int)

    def handle(self, *args, **options):
        query = '[out:json];area["de:amtlicher_gemeindeschluessel"~"^%s"];\
            foreach(\
             rel(pivot)->.a;\
             .a out meta;\
             (node(area)[amenity=%s][name];>;);\
             out qt meta;\
            );' % (options['gemeindeschluessel'][0], options['amenity'][0])

        r = requests.post('http://overpass-api.de/api/interpreter', data={'data': query})

        for node in r.json()['elements']:
            if node['type'] == 'node':
                obj = SearchPoi.objects.filter(osm_id=node['id'])
                if obj.count() == 0:
                    poi = SearchPoi()
                    poi.displayed_name = node['tags']['name']
                    poi.osm_id = node['id']
                    poi.osm_amenity = options['amenity'][0]
                    poi.geometry = {'type': 'Point', 'coordinates': [node['lon'], node['lat']]}
                    poi.save()
                    self.stdout.write("Created: %s" % node['tags']['name'])
