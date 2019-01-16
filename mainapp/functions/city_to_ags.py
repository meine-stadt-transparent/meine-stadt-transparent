from typing import Tuple, List

import requests

query_template = """
SELECT ?city ?cityLabel ?ags WHERE {{
  ?city wdt:P439 ?ags.
  ?city rdfs:label "{}"@de
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "de,en". }}
}}
"""
wikidata_sparql = "https://query.wikidata.org/sparql"


def city_to_ags(city_name: str) -> List[Tuple[str, str]]:
    query = query_template.format(city_name)
    response = requests.get(wikidata_sparql, {"format": "json", "query": query})
    response.raise_for_status()
    values = response.json()["results"]["bindings"]
    return [(i["cityLabel"]["value"], i["ags"]["value"]) for i in values]
