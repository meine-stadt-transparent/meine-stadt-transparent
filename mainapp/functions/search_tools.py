import datetime
from collections import namedtuple
from typing import Dict

from django.conf import settings
from django.urls import reverse
from django.utils.html import escape
from django.utils.translation import ugettext
from elasticsearch_dsl import Q, FacetedSearch, TermsFacet
from requests.utils import quote

from mainapp.functions.geo_functions import latlng_to_address

# Keep in sync with: mainapp/assets/js/FacettedSearch.js
QUERY_KEYS = [
    "document-type",
    "radius",
    "lat",
    "lng",
    "person",
    "organization",
    "after",
    "before",
    "sort",
]
# We technically only need an explicit list for elasticsearch 6, but it's counter-productive if
# we optimize for _all now and then have to redo the effort for elasticsearch 6
MULTI_MATCH_FIELDS = [
    "agenda_items.title",
    "body.name",
    "description",
    "displayed_filename",
    "family_name",
    "given_name",
    "name",
    "parsed_text",
    "short_name",
    "type",
]

NotificationSearchResult = namedtuple(
    "NotificationSearchResult", ["title", "url", "type", "type_name", "highlight"]
)


class MainappSearch(FacetedSearch):
    index = settings.ELASTICSEARCH_INDEX
    fields = MULTI_MATCH_FIELDS

    facets = {
        # use bucket aggregations to define facets
        "document_type": TermsFacet(field="_type"),
        "person": TermsFacet(field="person_ids"),
        "organization": TermsFacet(field="organization_ids"),
    }

    def __init__(self, params: Dict[str, str], offset=None, limit=None):
        self.params = params
        self.errors = []
        self.offset = offset
        self.limit = limit

        # Note that for django templates it makes a difference if a value is undefined or None
        self.options = {}

        filters = {
            "person": self.params.get("person"),
            "organization": self.params.get("organization"),
        }

        for key, value in filters.items():
            if value:
                self.options[key] = value

        if "document-type" in self.params:
            split = self.params["document-type"].split(",")
            self.options["document_type"] = split
            filters["document_type"] = [i + "_document" for i in split]

        if "sort" in self.params:
            if self.params["sort"] == "date_newest":
                sort = "-sort_date"
            elif self.params["sort"] == "date_oldest":
                sort = "sort_date"
            else:
                sort = "_score"
            self.options["sort"] = self.params["sort"]
        else:
            sort = "_score"

        super().__init__(self.params.get("searchterm"), filters, sort)

    def highlight(self, search):
        search = search.highlight_options(require_field_match=False)
        search = search.highlight(
            "*", fragment_size=150, pre_tags="<mark>", post_tags="</mark>"
        )
        return search

    def query(self, search, query):
        if query:
            self.options["searchterm"] = query
            # Fuzzines AUTO(=2) gives more error tolerance, but is also a lot slower and has many false positives
            search = search.query(
                "multi_match",
                **{
                    "query": escape_elasticsearch_query(query),
                    "operator": "and",
                    "fields": self.fields,
                    "fuzziness": "1",
                    "prefix_length": 1,
                }
            )

        return search

    def search(self):
        search = super().search()
        try:
            lat = float(self.params.get("lat", ""))
            lng = float(self.params.get("lng", ""))
            radius = int(self.params.get("radius", ""))
            search = search.filter(
                "geo_distance",
                distance=str(radius) + "m",
                coordinates={"lat": lat, "lon": lng},
            )
            self.options["lat"] = str(lat)
            self.options["lng"] = str(lng)
            self.options["radius"] = str(radius)
            self.options["location_formatted"] = latlng_to_address(lat, lng)
        except ValueError:
            pass

        if "after" in self.params:
            # options['after'] added by _add_date_after
            search = _add_date_after(search, self.params, self.options, self.errors)
        if "before" in self.params:
            # options['before'] added by _add_date_before
            search = _add_date_before(search, self.params, self.options, self.errors)

        # N.B.: indexing reset from and size
        if self.limit:
            if self.offset:
                search = search[self.offset : self.limit + self.offset]
            else:
                search = search[: self.limit]

        return search


def _add_date_after(search, params, options, errors):
    """ Filters by a date given a string, catching parsing errors. """
    try:
        after = datetime.datetime.strptime(params["after"], "%Y-%m-%d")
    except ValueError or OverflowError:
        errors.append(
            ugettext("The value for after is invalid. The correct format is YYYY-MM-DD")
        )
        return search
    search = search.filter(
        Q("range", start={"gte": after}) | Q("range", legal_date={"gte": after})
    )
    options["after"] = after
    return search


def _add_date_before(search, params, options, errors):
    """ Filters by a date given a string, catching parsing errors. """
    try:
        before = datetime.datetime.strptime(params["before"], "%Y-%m-%d")
    except ValueError or OverflowError:
        errors.append(
            ugettext("The value for after is invalid. The correct format is YYYY-MM-DD")
        )
        return search
    search = search.filter(
        Q("range", start={"lte": before}) | Q("range", legal_date={"lte": before})
    )
    options["before"] = before
    return search


def escape_elasticsearch_query(query):
    return query.replace("/", "\/")


def html_escape_highlight(highlight):
    escaped = escape(highlight)
    escaped = escaped.replace("&lt;mark&gt;", "<mark>").replace(
        "&lt;/mark&gt;", "</mark>"
    )
    return escaped


def search_string_to_params(query: str):
    query = query.replace("  ", " ").strip(
        " "
    )  # Normalize so we don't get empty splits
    values = [value.strip() for value in query.split(" ")]
    keys = QUERY_KEYS
    params = dict()
    for value in values[:]:
        for key in keys:
            if value.startswith(key + ":"):
                values.remove(value)
                value = value[len(key + ":") :]
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


def get_highlights(hit, parsed):
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
    return highlights


def parse_hit(hit, highlighting=True):
    # python module wtf
    from mainapp.documents import DOCUMENT_TYPE_NAMES

    parsed = hit.to_dict()
    parsed["type"] = hit.meta.doc_type.replace("_document", "").replace("_", "-")
    parsed["type_translated"] = DOCUMENT_TYPE_NAMES[parsed["type"]]
    parsed["url"] = reverse(parsed["type"], args=[hit.id])

    if highlighting:
        highlights = get_highlights(hit, parsed)
        if len(highlights) > 0:
            parsed["highlight"] = html_escape_highlight(highlights[0])
            parsed["highlight_extracted"] = (
                highlights[0].split("<mark>")[1].split("</mark>")[0]
            )
        else:
            parsed["highlight"] = None
            parsed["highlight_extracted"] = None
        parsed["name_escaped"] = html_escape_highlight(parsed["name"])

        if hit.type == "file" and hit.highlight_extracted:
            parsed["url"] += "?pdfjs_search=" + quote(parsed["highlight_extracted"])

    return parsed
