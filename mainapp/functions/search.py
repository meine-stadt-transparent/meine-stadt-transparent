import json
import logging
from collections import namedtuple
from typing import Dict, Optional, Any, List, Type
from urllib.parse import quote

from dateutil.parser import parse
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Model
from django.db.models.query import QuerySet
from django.urls import reverse
from django.utils.html import escape
from django.utils.translation import gettext, pgettext
from django_elasticsearch_dsl.registries import registry
from elasticsearch import TransportError
from elasticsearch_dsl import Q, FacetedSearch, TermsFacet, Search, AttrDict
from elasticsearch_dsl.query import Bool, MultiMatch, Query
from elasticsearch_dsl.response import Response

from mainapp.functions.geo_functions import latlng_to_address

logger = logging.getLogger(__name__)

DOCUMENT_TYPES = ["file", "meeting", "paper", "organization", "person"]

DOCUMENT_TYPE_NAMES = {
    "file": pgettext("Document Type Name", "File"),
    "meeting": pgettext("Document Type Name", "Meeting"),
    "paper": pgettext("Document Type Name", "Paper"),
    "organization": pgettext("Document Type Name", "Organization"),
    "person": pgettext("Document Type Name", "Person"),
}
DOCUMENT_TYPE_NAMES_PL = {
    "file": pgettext("Document Type Name", "Files"),
    "meeting": pgettext("Document Type Name", "Meetings"),
    "paper": pgettext("Document Type Name", "Papers"),
    "organization": pgettext("Document Type Name", "Organizations"),
    "person": pgettext("Document Type Name", "Persons"),
}

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

MULTI_MATCH_FIELDS = [
    "agenda_items.title",
    "body.name",
    "description",
    "filename",
    "family_name",
    "given_name",
    "name",
    "parsed_text^0.5",
    "short_name",
    "type",
    "reference_number",
]

NotificationSearchResult = namedtuple(
    "NotificationSearchResult", ["title", "url", "type", "type_name", "highlight"]
)


def get_document_indices():
    """We can't make this a constant because we want to change ELASTICSEARCH_PREFIX is the tests"""
    return {
        doc_type: settings.ELASTICSEARCH_PREFIX + "-" + doc_type
        for doc_type in DOCUMENT_TYPES
    }


class ElasticsearchNotAvailableError(Exception):
    def __str__(self):
        return (
            f"Couldn't connect to elasticsearch at {settings.ELASTICSEARCH_URL}. "
            f"See error trace for details"
        )


class MainappSearch(FacetedSearch):
    fields = MULTI_MATCH_FIELDS
    # use bucket aggregations to define facets
    facets = {
        "document_type": TermsFacet(field="_index"),
        "person": TermsFacet(field="person_ids"),
        "organization": TermsFacet(field="organization_ids"),
    }

    def __init__(
        self,
        params: Dict[str, str],
        offset: Optional[int] = None,
        limit: Optional[int] = None,
        extra_filter: Optional[List[Query]] = None,
    ):
        self.params = params
        self.errors = []
        self.offset = offset
        self.limit = limit
        self.index = list(get_document_indices().values())
        self.extra_filter: List[Query] = extra_filter or []

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
            filters["document_type"] = [
                settings.ELASTICSEARCH_PREFIX + "-" + i for i in split
            ]

        if "sort" in self.params:
            if self.params["sort"] == "date_newest":
                sort = ["-sort_date"]
            elif self.params["sort"] == "date_oldest":
                sort = ["sort_date"]
            else:
                sort = ["_score"]
            self.options["sort"] = self.params["sort"]
        else:
            sort = ["_score"]

        super().__init__(self.params.get("searchterm"), filters, sort)

    def highlight(self, search: Search) -> Search:
        # TODO: Why did we have this?
        # search = search.highlight_options(require_field_match=False)
        search = search.highlight(
            "*", fragment_size=150, pre_tags="<mark>", post_tags="</mark>"
        )
        return search

    def query(self, search: Search, query: str) -> Search:
        if query:
            self.options["searchterm"] = query
            # Fuzziness AUTO(=2) gives more error tolerance, but is also a lot slower and has many false positives
            # We're using https://stackoverflow.com/a/35375562/3549270 to make exact matches score higher than fuzzy
            # matches
            search = search.query(
                Bool(
                    should=[
                        MultiMatch(
                            query=escape_elasticsearch_query(query),
                            operator="and",
                            fields=self.fields,
                        ),
                        MultiMatch(
                            query=escape_elasticsearch_query(query),
                            operator="and",
                            fields=self.fields,
                            fuzziness="1",
                            prefix_length=1,
                        ),
                    ]
                )
            )
        return search

    def search(self) -> Search:
        search = super().search()  # type: Search
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

        for extra_filter in self.extra_filter:
            search = search.filter(extra_filter)

        # indices_boost: Titles often repeat the organization name and the test contains person names, but
        # when searching for those proper nouns, the person/organization itself should be at the top
        # _source: Take only the fields we use, and especially ignore the huge parsed_text
        search.update_from_dict(
            {
                "indices_boost": [
                    {get_document_indices()["person"]: 4},
                    {get_document_indices()["organization"]: 4},
                    {get_document_indices()["paper"]: 2},
                ],
                "_source": [
                    "id",
                    "name",
                    "legal_date",
                    "reference_number",
                    "display_date",
                ],
            }
        )

        # N.B.: indexing reset from and size
        if self.limit:
            if self.offset:
                search = search[self.offset : self.limit + self.offset]
            else:
                search = search[: self.limit]

        return search

    def build_search(self) -> Search:
        search = super().build_search()
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(
                "Elasticsearch query: {}".format(
                    json.dumps(search.to_dict(), cls=DjangoJSONEncoder)
                )
            )
        return search

    def execute(self):
        # Return a more useful error message in debug mode
        try:
            return super().execute()
        except TransportError as e:
            raise ElasticsearchNotAvailableError() from e


def _add_date_after(
    search: Search, params: Dict[str, Any], options, errors: List[str]
) -> Search:
    """Filters by a date given a string, catching parsing errors."""
    try:
        after = parse(params["after"])
    except (ValueError, OverflowError) as e:
        errors.append(
            gettext(
                f"The value for after is invalid. The correct format is 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS': {e}"
            )
        )
        return search
    search = search.filter(
        Q("range", start={"gte": after}) | Q("range", legal_date={"gte": after})
    )
    options["after"] = after
    return search


def _add_date_before(search: Search, params: Dict[str, Any], options, errors) -> Search:
    """Filters by a date given a string, catching parsing errors."""
    try:
        before = parse(params["before"])
    except (ValueError, OverflowError) as e:
        errors.append(
            gettext(
                f"The value for before is invalid. The correct format is 'YYYY-MM-DD' or 'YYYY-MM-DD HH:MM:SS': {e}"
            )
        )
        return search
    search = search.filter(
        Q("range", start={"lte": before}) | Q("range", legal_date={"lte": before})
    )
    options["before"] = before
    return search


def escape_elasticsearch_query(query: str) -> str:
    return query.replace("/", "\\/")


def html_escape_highlight(highlight: Optional[str]) -> Optional[str]:
    if not highlight:
        return None
    escaped = escape(highlight)
    escaped = escaped.replace("&lt;mark&gt;", "<mark>").replace(
        "&lt;/mark&gt;", "</mark>"
    )
    return escaped


def search_string_to_params(query: str) -> Dict[str, Any]:
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


def params_to_search_string(params: Dict[str, Any]) -> str:
    values = []
    for key, value in sorted(params.items()):
        if key != "searchterm":
            values.append(key + ":" + str(value))
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
                elif field_name == "reference_number":
                    parsed["reference_number"] = field_highlight
                elif field_name == "short_name":
                    pass
                else:
                    highlights.append(field_highlight)
    return highlights


def parse_hit(hit: AttrDict, highlighting: bool = True) -> Dict[str, Any]:
    parsed = hit.to_dict()  # Adds name and reference_number if available
    parsed["type"] = hit.meta.index.split("-")[-1]
    parsed["type_translated"] = DOCUMENT_TYPE_NAMES[parsed["type"]]
    parsed["url"] = reverse(parsed["type"], args=[hit.id])
    parsed["score"] = hit.meta.score

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

        if hit.type == "file" and hit.highlight_extracted:
            parsed["url"] += "?pdfjs_search=" + quote(parsed["highlight_extracted"])

    parsed["name_escaped"] = html_escape_highlight(parsed["name"])
    parsed["reference_number_escaped"] = html_escape_highlight(
        parsed.get("reference_number")
    )

    return parsed


def autocomplete(query: str) -> Response:
    """
    https://www.elastic.co/guide/en/elasticsearch/guide/current/_index_time_search_as_you_type.html
    We use the ngram-based autocomplete-analyzer for indexing, but the standard analyzer for searching
    This way we enforce that the whole entered word has to be matched (save for some fuzziness) and the algorithm
    does not fall back to matching only the first character in extreme cases. This prevents absurd cases where
    "Garret Walker" and "Hector Mendoza" are suggested when we're entering "Mahatma Ghandi"
    """
    search_query = Search(index=list(get_document_indices().values()))
    search_query = search_query.query(
        "match",
        autocomplete={
            "query": escape_elasticsearch_query(query),
            "analyzer": "standard",
            "fuzziness": "AUTO",
            "prefix_length": 1,
        },
    )
    search_query = search_query.extra(min_score=1)
    search_query = search_query.update_from_dict(
        {
            "indices_boost": [
                {get_document_indices()["person"]: 4},
                {get_document_indices()["organization"]: 4},
                {get_document_indices()["paper"]: 2},
            ]
        }
    )
    response = search_query.execute()
    return response


def search_bulk_index(model: Type[Model], qs: QuerySet, **kwargs):
    """Django orm bulk functions such as `bulk_create`, `bulk_index` and
    `update`do not send signals for the modified objects and therefore do not
    automatically update the elasticsearch index. This function therefore
    bulk-reindexes the changed objects."""
    [current_doc] = registry.get_documents([model])
    return current_doc().update(qs, **kwargs)
