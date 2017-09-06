from django.core.management.base import BaseCommand
import requests

from mainapp.models import SearchStreet


class Command(BaseCommand):
    help = 'Closes the specified poll for voting'

    def add_arguments(self, parser):
        parser.add_argument('gemeindeschluessel', nargs=1, type=str)
        parser.add_argument('body-id', nargs=1, type=int)

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Importing streets from %s' % options['gemeindeschluessel'][0]))

        query = '[out:json];area["de:amtlicher_gemeindeschluessel"~"^%s"];\
            foreach(\
             rel(pivot)->.a;\
             .a out meta;\
             (way(area)[highway~"^residential$|^service$|^unclassified$|^track$|^footway$|^tertiary$|^path$|^secondary$|^primary$|^cycleway$|^trunk$|^living_street$|^road$|^pedestrian$|^construction$"][name];>;);\
             out qt meta;\
            );' % options['gemeindeschluessel'][0]

        r = requests.post('http://overpass-api.de/api/interpreter', data={'data': query})

        for node in r.json()['elements']:
            if node['type'] == 'way':
                obj = SearchStreet.objects.filter(osm_id=node['id'])
                if obj.count() == 0:
                    street = SearchStreet()
                    street.displayed_name = node['tags']['name']
                    street.osm_id = node['id']
                    street.save()
                    self.stdout.write("Created: %s" % node['tags']['name'])
