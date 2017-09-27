import json

import os
import requests
import subprocess
from django.core.management.base import BaseCommand

from mainapp.models import Body, Location


class Command(BaseCommand):
    help = 'Imports the outlines from OpenStreetMap for a given city (amtlicher_gemeindeschluessel=gemeideschlüssel)'

    def add_arguments(self, parser):
        parser.add_argument('gemeindeschluessel', type=str)
        parser.add_argument('body-id', type=int)

    def convert_to_geojson(self, osm):
        tmpfile = '/tmp/city-outline.json'
        file = open(tmpfile, 'w')
        file.write(osm)
        file.close()

        result = subprocess.run(['node_modules/.bin/osmtogeojson', '-f', 'json', '-m', tmpfile], stdout=subprocess.PIPE)
        geojson = result.stdout.decode('utf-8')

        os.remove(tmpfile)
        return geojson

    def handle(self, *args, **options):
        body = Body.objects.get(id=options['body-id'])
        if not body:
            self.stderr.write("Body not found: %s" % options['body-id'])
            return

        if not body.outline:
            outline = Location()
            outline.name = 'Outline of ' + body.name
            outline.short_name = body.short_name
            outline.is_official = False
        else:
            outline = body.outline

        self.stdout.write(self.style.SUCCESS('Importing outline from %s' % options['gemeindeschluessel']))

        query = '[out:json];area["de:amtlicher_gemeindeschluessel"~"^%s"]->.cityarea;rel(pivot.cityarea);out geom;'\
                % options['gemeindeschluessel']

        r = requests.post('http://overpass-api.de/api/interpreter', data={'data': query})

        geojson = self.convert_to_geojson(r.text)
        outline.geometry = geojson
        outline.save()

        body.outline = outline
        body.save()
