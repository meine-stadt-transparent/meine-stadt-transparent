"""
Resources:
 * https://www.riserid.eu/data/user_upload/downloads/info-pdf.s/Diverses/Liste-Amtlicher-Gemeindeschluessel-AGS-2015.pdf
 * https://de.wikipedia.org/wiki/Liste_der_Landkreise_in_Deutschland
 * Test the query: https://query.wikidata.org/#SELECT%20DISTINCT%20%3Fcity%20%3FcityLabel%20%3Fags%20WHERE%20%7B%0A%20%20%7B%20%3Fcity%20rdfs%3Alabel%20%22Ahrweiler%22.%20%7D%0A%20%20UNION%0A%20%20%7B%20%3Fcity%20rdfs%3Alabel%20%22Ahrweiler%22%40de.%20%7D%0A%20%20UNION%0A%20%20%7B%20%3Fcity%20rdfs%3Alabel%20%22Ahrweiler%22%40en.%20%7D%0A%20%20%7B%20%3Fcity%20wdt%3AP440%20%3Fags.%20%7D%0A%20%20UNION%0A%20%20%7B%20%3Fcity%20wdt%3AP439%20%3Fags.%20%7D%0A%20%20SERVICE%20wikibase%3Alabel%20%7B%20bd%3AserviceParam%20wikibase%3Alanguage%20%22de%2Cen%22.%20%7D%0A%7D%0A
"""

from typing import Tuple, List, Optional

import requests

query_template = """
SELECT DISTINCT ?city ?cityLabel ?ags WHERE {{
  {{ ?city rdfs:label "{0}". }}
  UNION
  {{ ?city rdfs:label "{0}"@de. }}
  UNION
  {{ ?city rdfs:label "{0}"@en. }}
  {{ ?city wdt:P440 ?ags. }}
  UNION
  {{ ?city wdt:P439 ?ags. }}
  SERVICE wikibase:label {{ bd:serviceParam wikibase:language "de,en". }}
}}
"""
wikidata_sparql = "https://query.wikidata.org/sparql"


def city_to_ags_all(city_name: str) -> List[Tuple[str, str]]:
    query = query_template.format(city_name)
    response = requests.get(wikidata_sparql, {"format": "json", "query": query})
    response.raise_for_status()
    data = response.json()
    values = data["results"]["bindings"]
    pairs = set()
    for i in values:
        city = i["cityLabel"]["value"]
        value = i["ags"]["value"]
        if len(value) != 5 and len(value) != 8:
            raise RuntimeError(
                "Invalid Amtlicher Gemeindeschlüssel: '{}'".format(value)
            )
        pairs.add((city, value))

    return list(pairs)


def city_to_ags(city_name: str, district: bool) -> Optional[str]:
    """Returns the Amtliche Gemeindeschlüssel"""
    ags_list = city_to_ags_all(city_name)
    if len(ags_list) == 0:
        return None
    elif len(ags_list) == 1:
        return ags_list[0][1]
    else:
        # Try to disambiguate between district and city
        districts = []
        cities = []
        for single_ags in ags_list:
            if len(single_ags[1]) == 8:
                cities.append(single_ags)
            else:
                districts.append(single_ags)
        if district and len(districts) == 1:
            return districts[0][1]
        if not district and len(cities) == 1:
            return cities[0][1]

    return None
