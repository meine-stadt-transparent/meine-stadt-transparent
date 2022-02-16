from django.core.management.base import BaseCommand

from mainapp.functions.city_to_ags import city_to_ags_all


class Command(BaseCommand):
    help = "Queries wikidata to get the ags of a city"

    def add_arguments(self, parser):
        parser.add_argument("city-name", type=str)

    def handle(self, *args, **options):
        results = city_to_ags_all(options["city-name"])
        if not results:
            self.stdout.write(self.style.NOTICE("Not found"))
        for i in results:
            self.stdout.write("{} {}\n".format(i[0], i[1]))
