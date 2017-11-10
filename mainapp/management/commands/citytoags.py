from django.core.management.base import BaseCommand

from importer import CityToAGS


class Command(CityToAGS, BaseCommand):
    help = 'Queries wikidata to map a city name to an ags'

    def add_arguments(self, parser):
        parser.add_argument('city-name', type=str)

    def handle(self, *args, **options):
        for i in self.query_wikidata(options["city-name"]):
            print(i[0], i[1])
