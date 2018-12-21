from typing import Tuple, List

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

    @classmethod
    def query_wikidata(cls, city_name: str) -> List[Tuple[str, str]]:
        query = cls.query_template.format(city_name)
        response = requests.get(cls.base_url, {"format": "json", "query": query})
        response.raise_for_status()
        values = response.json()["results"]["bindings"]
        return [(i["cityLabel"]["value"], i["ags"]["value"]) for i in values]
