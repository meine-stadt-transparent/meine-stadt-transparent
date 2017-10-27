from django.conf import settings
from elasticsearch_dsl import Search


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
    return options, s


def search_string_to_params(query: str):
    values = [value.strip() for value in query.split(" ")]
    keys = ["body", "radius", "lat", "lng"]
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
