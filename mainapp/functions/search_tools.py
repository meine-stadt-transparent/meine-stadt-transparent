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
        s = s.filter("geo_distance", distance=str(radius) + "m", coordinates={
            "lat": lat,
            "lon": lng,
        })
        options['lat'] = lat
        options['lng'] = lng
        options['radius'] = radius
    except ValueError:
        pass
    return options, s
