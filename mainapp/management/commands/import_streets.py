from django.core.management.base import BaseCommand, CommandError

from mainapp.functions.citytools import import_streets
from mainapp.models import Body


class Command(BaseCommand):
    help = "Imports streets from OpenStreetMap for a given city"

    def add_arguments(self, parser):
        parser.add_argument("body-id", type=int)
        parser.add_argument("--ags", type=str, help="The Amtliche Gemeindeschlüssel")

    def handle(self, *args, **options):
        body = Body.objects.get(id=options["body-id"])
        ags = options["ags"] or body.ags
        if not ags:
            raise CommandError(
                "The body doesn't have an associated amtliche Gemeindeschlüssel, please provide one with --ags"
            )

        import_streets(body, ags)
