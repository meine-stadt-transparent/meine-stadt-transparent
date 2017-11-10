import requests


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
