import datetime

from django.conf import settings
from django.urls import reverse
from django.utils.html import escape
from django.utils.translation import ugettext, pgettext
from elasticsearch_dsl import Search, Q

from mainapp.functions.geo_functions import latlng_to_address
from meine_stadt_transparent.settings import ABSOLUTE_URI_BASE

QUERY_KEYS = ["document-type", "radius", "lat", "lng", "person", "after", "before"]


class NotificationSearchResult:
    title = None
    url = None
    type = None
    type_name = None

    def __init__(self, title, url, type_id, type_name):
        self.title = title
        self.url = url
        self.type = type_id
        self.type_name = type_name


def _add_date_after(s, raw, options, errors):
    """ Filters by a date given a string, catching parsing errors. """
    try:
        after = datetime.datetime.strptime(raw['after'], '%Y-%m-%d')
        s = s.filter(Q('range', start={"gte": after}) | Q('range', legal_date={"gte": after}))
        options["after"] = after
    except ValueError or OverflowError:
        errors.append(ugettext('The value for after is invalid. The correct format is YYYY-MM-DD'))
    return s


def _add_date_before(s, raw, options, errors):
    """ Filters by a date given a string, catching parsing errors. """
    try:
        before = datetime.datetime.strptime(raw['before'], '%Y-%m-%d')
        s = s.filter(Q('range', start={"lte": before}) | Q('range', legal_date={"lte": before}))
        options["before"] = before
    except ValueError or OverflowError:
        errors.append(ugettext('The value for after is invalid. The correct format is YYYY-MM-DD'))
    return s


def add_modified_since(s, since: datetime):
    s = s.filter(Q('range', modified={'gte': since}))
    return s


def _escape_elasticsearch_query(query):
    escaped = query.replace('/', '\/')
    return escaped


def html_escape_highlight(highlight):
    escaped = escape(highlight)
    escaped = escaped.replace('&lt;mark&gt;', '<mark>').replace('&lt;/mark&gt;', '</mark>')
    return escaped


def params_to_query(params: dict):
    s = Search(index=settings.ELASTICSEARCH_INDEX)
    options = {}
    errors = []
    if 'searchterm' in params and params['searchterm'] is not "":
        s = s.query('match', _all={
            'query': _escape_elasticsearch_query(params['searchterm']),
            'operator': 'and',
            'fuzziness': 'AUTO',
            'prefix_length': 1
        })
        s = s.highlight_options(require_field_match=False)
        s = s.highlight('*', fragment_size=150, pre_tags='<mark>', post_tags='</mark>')
        options['searchterm'] = params['searchterm']

    try:
        lat = float(params.get('lat', ''))
        lng = float(params.get('lng', ''))
        radius = int(params.get('radius', ''))
        s = s.filter("geo_distance", distance=str(radius) + "m", coordinates={
            "lat": lat,
            "lon": lng,
        })
        options['lat'] = str(lat)
        options['lng'] = str(lng)
        options['radius'] = str(radius)
        options['location_formatted'] = latlng_to_address(lat, lng)
    except ValueError:
        pass

    if 'document-type' in params:
        split = params['document-type'].split(",")
        s = s.filter('terms', _type=[i + "_document" for i in split])
        options["document_type"] = split
    if 'after' in params:
        s = _add_date_after(s, params, options, errors)
    if 'before' in params:
        s = _add_date_before(s, params, options, errors)

    return options, s, errors


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


def params_are_equal(params1: dict, params2: dict):
    return params_to_search_string(params1) == params_to_search_string(params2)


def params_are_subscribable(params: dict):
    if 'after' in params:
        return False
    if 'before' in params:
        return False
    return True


def search_result_for_notification(result):
    from mainapp.documents import DOCUMENT_TYPE_NAMES

    if result["type"] == "meeting":
        title = result["name"]
        url = ABSOLUTE_URI_BASE + reverse('meeting', args=[result["id"]])
    elif result["type"] == "paper":
        title = result["name"]
        url = ABSOLUTE_URI_BASE + reverse('paper', args=[result["id"]])
    elif result["type"] == "file":  # displayed_filename?
        title = result["name"]
        url = ABSOLUTE_URI_BASE + reverse('file', args=[result["id"]])
    else:
        title = "Unknown"
        url = ""

    return NotificationSearchResult(
        title=title,
        url=url,
        type_id=result["type"],
        type_name=DOCUMENT_TYPE_NAMES[result["type"]]
    )


def params_to_human_string(params: dict):
    from mainapp.documents import DOCUMENT_TYPE_NAMES_PL

    if 'document-type' in params:
        split = params['document-type'].split(",")
        what = []
        for el in split:
            what.append(DOCUMENT_TYPE_NAMES_PL[el])
        if len(what) > 1:
            last_el = what.pop()
            description = ", ".join(what)
            description += " " + pgettext('Search query', 'and') + " " + last_el
        else:
            description = what[0]

    else:
        description = pgettext('Search query', 'Documents')

    strs = []

    if 'searchterm' in params and params['searchterm'] != '':
        strs.append(pgettext('Search query', 'containing "%STR%"').replace('%STR%', params['searchterm']))

    if 'person' in params:
        strs.append(pgettext('Search query', 'created by %FROM%').replace('%BY%', params['person']))

    if 'radius' in params:
        place_name = latlng_to_address(params['lat'], params['lng'])
        locstr = pgettext('Search query', 'with a location within %DISTANCE%m around "%PLACE%"')
        strs.append(locstr.replace('%DISTANCE%', params['radius']).replace('%PLACE%', place_name))

    if 'before' in params and 'after' in params:
        strs.append(pgettext('Search query', 'published from %FROM% to %TO%').replace('%FROM%', params['after']).replace('%TO%', params['before']))
    elif 'before' in params:
        strs.append(pgettext('Search query', 'published before %TO%').replace('%TO%', params['before']))
    elif 'after' in params:
        strs.append(pgettext('Search query', 'published after %FROM%').replace('%FROM%', params['after']))

    if len(strs) > 0:
        description += " " + ", ".join(strs)

    return description
