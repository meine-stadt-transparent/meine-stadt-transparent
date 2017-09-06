import requests
from django.core.management.base import BaseCommand

from mainapp.models import SearchStreet, Body


class Command(BaseCommand):
    help = 'Closes the specified poll for voting'

    def add_arguments(self, parser):
        parser.add_argument('gemeindeschluessel', type=str)
        parser.add_argument('body-id', type=int)

    def handle(self, *args, **options):
        body = Body.objects.filter(id=options['body-id'])
        if body.count() == 0:
            self.stderr.write("Body not found: %s" % options['body-id'])
            return

        self.stdout.write(self.style.SUCCESS('Importing streets from %s' % options['gemeindeschluessel']))

        query = '[out:json];area["de:amtlicher_gemeindeschluessel"~"^%s"];\
            foreach(\
             rel(pivot)->.a;\
             .a out meta;\
             (way(area)[highway~"^residential$|^service$|^unclassified$|^track$|^footway$|^tertiary$|^path$|^secondary$|^primary$|^cycleway$|^trunk$|^living_street$|^road$|^pedestrian$|^construction$"][name];>;);\
             out qt meta;\
            );' % options['gemeindeschluessel']

        r = requests.post('http://overpass-api.de/api/interpreter', data={'data': query})

        for node in r.json()['elements']:
            if node['type'] == 'way':
                obj = SearchStreet.objects.filter(osm_id=node['id'])
                if obj.count() == 0:
                    street = SearchStreet()
                    street.displayed_name = node['tags']['name']
                    street.osm_id = node['id']
                    street.save()

                    street.bodies.add(body[0])

                    self.stdout.write("Created: %s" % node['tags']['name'])
