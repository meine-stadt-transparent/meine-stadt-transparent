import requests
from django.core.management.base import BaseCommand

from importer.citytools import convert_to_geojson, import_outline
from mainapp.models import Body, Location


class Command(BaseCommand):
    help = 'Imports the outlines from OpenStreetMap for a given city (amtlicher_gemeindeschluessel=gemeideschlüssel)'

    def add_arguments(self, parser):
        parser.add_argument('gemeindeschluessel', type=str)
        parser.add_argument('body-id', type=int)
        parser.add_argument('--tmpfile', type=str, default='/tmp/city-outline.json')

    def handle(self, *args, **options):
        import_outline(options["body-id"], options["gemeindeschluessel"], options["tmpfile"])
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

        geojson = convert_to_geojson(r.text, options["tmpfile"])
        outline.geometry = geojson
        outline.save()

        body.outline = outline
        body.save()


