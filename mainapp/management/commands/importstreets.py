import requests
from django.core.management.base import BaseCommand

from mainapp.models import SearchStreet, Body


class Command(BaseCommand):
    help = 'Imports streets from OpenStreetMap for a given city (amtlicher_gemeindeschluessel=gemeideschlüssel)'

    query_template = """
    [out:json];area["de:amtlicher_gemeindeschluessel"~"^{}"];
    foreach(
        rel(pivot)->.a;
        .a out meta;
        (way(area)[highway~"^residential$|^service$|^unclassified$|^track$|^footway$|^tertiary$|^path$|^secondary$|^primary$|^cycleway$|^trunk$|^living_street$|^road$|^pedestrian$|^construction$"][name];>;);
        out qt meta;
    );
    """

    def add_arguments(self, parser):
        parser.add_argument('gemeindeschluessel', type=str)
        parser.add_argument('body-id', type=int)

    def handle(self, *args, **options):
        body = Body.objects.get(id=options['body-id'])

        self.stdout.write(self.style.SUCCESS('Importing streets from %s' % options['gemeindeschluessel']))

        query = self.query_template.format(options['gemeindeschluessel'])

        r = requests.post('http://overpass-api.de/api/interpreter', data={'data': query})

        for node in r.json()['elements']:
            if node['type'] == 'way':
                obj = SearchStreet.objects.filter(osm_id=node['id'])
                if obj.count() == 0:
                    street = SearchStreet()
                    street.displayed_name = node['tags']['name']
                    street.osm_id = node['id']
                    street.save()

                    street.bodies.add(body)

                    self.stdout.write("Created: %s" % node['tags']['name'])
