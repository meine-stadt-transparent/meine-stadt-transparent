from django.conf import settings
from elasticsearch_dsl import Search

QUERY_KEYS = ["document-type", "radius", "lat", "lng"]


def params_to_query(params: dict):
    s = Search(index=settings.ELASTICSEARCH_INDEX)
    options = {}
    if 'searchterm' in params:
        s = s.query('query_string', query=params['searchterm'])
        options['searchterm'] = params['searchterm']
    if 'query' in params:
        s = s.filter("match", parsed_text=params['query'])
        s = s.highlight('parsed_text', fragment_size=50)  # @TODO Does not work yet
    try:
        lat = float(params.get('lat', ''))
        lng = float(params.get('lng', ''))
        radius = int(params.get('radius', ''))
        s = s.filter("geo_distance", distance=str(radius) + "m", location={
            "lat": lat,
            "lon": lng,
        })
        options['lat'] = str(lat)
        options['lng'] = str(lng)
        options['radius'] = str(radius)
    except ValueError:
        pass
    if 'document-type' in params:
        split = params['document-type'].split(",")
        s = s.filter('terms', _type=[i + "_document" for i in split])
        options["document_type"] = split
    return options, s


def search_string_to_params(query: str):
    values = [value.strip() for value in query.split(" ")]
    keys = QUERY_KEYS
    params = dict()
    for value in values[:]:
        for key in keys:
            if value.startswith(key + ":"):
                values.remove(value)
                value = value[len(key + ":"):]
                params[key] = value
    if len(values) > 0:
        params["searchterm"] = " ".join(values).replace("  ", " ").strip()
    return params


def params_to_search_string(params: dict):
    values = []
    for key, value in sorted(params.items()):
        if key != "searchterm":
            values.append(key + ":" + value)
    if "searchterm" in params:
        values.append(params["searchterm"])
    searchstring = " ".join(values)
    return searchstring
