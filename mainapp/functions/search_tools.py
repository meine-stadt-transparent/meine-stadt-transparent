import datetime
from collections import namedtuple

from django.conf import settings
from django.urls import reverse
from django.utils.html import escape
from django.utils.translation import ugettext, pgettext
from elasticsearch_dsl import Q, FacetedSearch, TermsFacet
from requests.utils import quote

from mainapp.functions.geo_functions import latlng_to_address
from mainapp.models import Person, Organization
from meine_stadt_transparent.settings import ABSOLUTE_URI_BASE

# Keep in sync with: mainapp/assets/js/FacettedSearch.js
QUERY_KEYS = ["document-type", "radius", "lat", "lng", "person", "organization", "after", "before", "sort"]

NotificationSearchResult = namedtuple("NotificationSearchResult", ["title", "url", "type", "type_name"])


class MainappSearch(FacetedSearch):
    index = settings.ELASTICSEARCH_INDEX
    fields = ["_all"]

    facets = {
        # use bucket aggregations to define facets
        'document_type': TermsFacet(field='_type'),
        'person': TermsFacet(field='person_ids'),
        'organization': TermsFacet(field='organization_ids'),
    }

    def __init__(self, params):
        self.params = params
        self.errors = []

        # Note that for django templates it makes a difference if a value is undefined or None
        self.options = {}

        filters = {
            'person': self.params.get('person'),
            'organization': self.params.get('organization')
        }

        for key, value in filters.items():
            if value:
                self.options[key] = value

        if 'document-type' in self.params:
            split = self.params['document-type'].split(",")
            self.options["document_type"] = split
            filters["document_type"] = [i + "_document" for i in split]

        if 'sort' in self.params:
            if self.params['sort'] == 'date_newest':
                sort = {"sort_date": {"order": "desc"}}
            elif self.params['sort'] == 'date_oldest':
                sort = {"sort_date": {"order": "asc"}}
            else:
                sort = "_score"
            self.options['sort'] = self.params['sort']
        else:
            sort = "_score"

        super().__init__(self.params.get("searchterm"), filters, sort)

    def highlight(self, search):
        search = search.highlight_options(require_field_match=False)
        search = search.highlight('*', fragment_size=150, pre_tags='<mark>', post_tags='</mark>')
        return search

    def query(self, search, query):
        if query:
            self.options["searchterm"] = query
            search = search.query('match', _all={
                'query': escape_elasticsearch_query(query),
                'operator': 'and',
                'fuzziness': 'AUTO',
                'prefix_length': 1
            })

        return search

    def search(self):
        s = super().search()
        try:
            lat = float(self.params.get('lat', ''))
            lng = float(self.params.get('lng', ''))
            radius = int(self.params.get('radius', ''))
            s = s.filter("geo_distance", distance=str(radius) + "m", coordinates={
                "lat": lat,
                "lon": lng,
            })
            self.options['lat'] = str(lat)
            self.options['lng'] = str(lng)
            self.options['radius'] = str(radius)
            self.options['location_formatted'] = latlng_to_address(lat, lng)
        except ValueError:
            pass

        if 'after' in self.params:
            # options['after'] added by _add_date_after
            s = _add_date_after(s, self.params, self.options, self.errors)
        if 'before' in self.params:
            # options['before'] added by _add_date_before
            s = _add_date_before(s, self.params, self.options, self.errors)

        return s


def _add_date_after(s, raw, options, errors):
    """ Filters by a date given a string, catching parsing errors. """
    try:
        after = datetime.datetime.strptime(raw['after'], '%Y-%m-%d')
    except ValueError or OverflowError:
        errors.append(ugettext('The value for after is invalid. The correct format is YYYY-MM-DD'))
        return s
    s = s.filter(Q('range', start={"gte": after}) | Q('range', legal_date={"gte": after}))
    options["after"] = after
    return s


def _add_date_before(s, raw, options, errors):
    """ Filters by a date given a string, catching parsing errors. """
    try:
        before = datetime.datetime.strptime(raw['before'], '%Y-%m-%d')
    except ValueError or OverflowError:
        errors.append(ugettext('The value for after is invalid. The correct format is YYYY-MM-DD'))
        return s
    s = s.filter(Q('range', start={"lte": before}) | Q('range', legal_date={"lte": before}))
    options["before"] = before
    return s


def add_modified_since(s, since: datetime):
    s = s.filter(Q('range', modified={'gte': since}))
    return s


def escape_elasticsearch_query(query):
    return query.replace('/', '\/')


def html_escape_highlight(highlight):
    escaped = escape(highlight)
    escaped = escaped.replace('&lt;mark&gt;', '<mark>').replace('&lt;/mark&gt;', '</mark>')
    return escaped


def search_string_to_params(query: str):
    query = query.replace("  ", " ").strip(" ")  # Normalize so we don't get empty splits
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
        params["searchterm"] = " ".join(values).strip()
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

    return NotificationSearchResult(title, url, result["type"], DOCUMENT_TYPE_NAMES[result["type"]])


def parse_hit(hit):
    # python module wtf
    from mainapp.documents import DOCUMENT_TYPE_NAMES

    parsed = hit.to_dict()
    parsed["type"] = hit.meta.doc_type.replace("_document", "").replace("_", "-")

    parsed["type_translated"] = DOCUMENT_TYPE_NAMES[parsed["type"]]
    highlights = []
    if hasattr(hit.meta, "highlight"):
        for field_name, field_highlights in hit.meta.highlight.to_dict().items():
            for field_highlight in field_highlights:
                if field_name == "name":
                    parsed["name"] = field_highlight
                elif field_name == "short_name":
                    pass
                else:
                    highlights.append(field_highlight)
    if len(highlights) > 0:
        parsed["highlight"] = html_escape_highlight(highlights[0])
        parsed["highlight_extracted"] = highlights[0].split("<mark>")[1].split("</mark>")[0]
    else:
        parsed["highlight"] = None
        parsed["highlight_extracted"] = None
    parsed["name_escaped"] = html_escape_highlight(parsed["name"])

    parsed["url"] = reverse(parsed["type"], args=[hit.id])
    if hit.type == "file" and hit.highlight_extracted:
        parsed["url"] += "?pdfjs_search=" + quote(parsed["highlight_extracted"])

    return parsed


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
        person = Person.objects.get(pk=params['person'])
        if person:
            strs.append(pgettext('Search query', 'mentioning %FROM%').replace('%FROM%', person.__str__()))

    if 'organization' in params:
        organization = Organization.objects.get(pk=params['organization'])
        if organization:
            strs.append(pgettext('Search query', 'assigned to %TO%').replace('%TO%', organization.__str__()))

    if 'radius' in params:
        place_name = latlng_to_address(params['lat'], params['lng'])
        locstr = pgettext('Search query', 'with a location within %DISTANCE%m around "%PLACE%"')
        strs.append(locstr.replace('%DISTANCE%', params['radius']).replace('%PLACE%', place_name))

    if 'before' in params and 'after' in params:
        strs.append(
            pgettext('Search query', 'published from %FROM% to %TO%')
                .replace('%FROM%', params['after'])
                .replace('%TO%', params['before']))
    elif 'before' in params:
        strs.append(pgettext('Search query', 'published before %TO%').replace('%TO%', params['before']))
    elif 'after' in params:
        strs.append(pgettext('Search query', 'published after %FROM%').replace('%FROM%', params['after']))

    if len(strs) > 0:
        description += " " + ", ".join(strs)

    return description
