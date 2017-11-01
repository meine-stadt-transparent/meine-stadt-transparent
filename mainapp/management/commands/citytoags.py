import requests
from django.core.management.base import BaseCommand


class CityToAGS:
    query_template = """
        SELECT ?city ?cityLabel ?ags WHERE {{
          ?city wdt:P439 ?ags.
          ?city rdfs:label "{}"@de
          SERVICE wikibase:label {{ bd:serviceParam wikibase:language "de,en". }}
        }}
    """
    base_url = "https://query.wikidata.org/sparql"

    def query_wikidata(self, city_name):
        query = self.query_template.format(city_name)
        response = requests.get(self.base_url, {"format": "json", "query": query})
        response.raise_for_status()
        parsed = response.json()
        for i in parsed["results"]["bindings"]:
            yield i["cityLabel"]["value"], i["ags"]["value"]


class Command(CityToAGS, BaseCommand):
    help = 'Queries wikidata to map a city name to an ags'

    def add_arguments(self, parser):
        parser.add_argument('city-name', type=str)

    def handle(self, *args, **options):
        for i in self.query_wikidata(options["city-name"]):
            print(i[0], i[1])
