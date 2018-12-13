import json
import logging

# noinspection PyPackageRequirements
from csp.decorators import csp_update
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.template import loader
from django.urls import reverse
from django.utils.translation import ugettext as _
from elasticsearch_dsl import Search

from mainapp.documents import DOCUMENT_TYPE_NAMES
from mainapp.functions.geo_functions import latlng_to_address
from mainapp.functions.search_tools import (
    search_string_to_params,
    escape_elasticsearch_query,
    MainappSearch,
    parse_hit,
    params_to_search_string,
)
from mainapp.functions.search_notification_tools import params_are_subscribable
from mainapp.models import Body, Organization, Person
from mainapp.views.utils import (
    handle_subscribe_requests,
    is_subscribed_to_search,
    build_map_object,
    NeedsLoginError,
)

logger = logging.getLogger(__name__)


def _search_to_context(query, main_search: MainappSearch, executed, results, request):
    context = {
        "query": query,
        "results": results,
        "options": main_search.options,
        "document_types": DOCUMENT_TYPE_NAMES,
        "map": build_map_object(),
        "pagination_length": settings.SEARCH_PAGINATION_LENGTH,
        "total_hits": executed.hits.total,
        "subscribable": params_are_subscribable(main_search.params),
        "is_subscribed": is_subscribed_to_search(request.user, main_search.params),
    }

    return context


@csp_update(STYLE_SRC=("'self'", "'unsafe-inline'"))
def search(request, query):
    params = search_string_to_params(query)
    normalized = params_to_search_string(params)
    main_search = MainappSearch(params, limit=settings.SEARCH_PAGINATION_LENGTH)

    for error in main_search.errors:
        messages.error(request, error)

    try:
        handle_subscribe_requests(
            request,
            params,
            _("You will now receive notifications about new search results."),
            _("You will no longer receive notifications."),
            _("You have already subscribed to this search."),
        )
    except NeedsLoginError as err:
        return redirect(err.redirect_url)

    executed = main_search.execute()
    results = [parse_hit(hit) for hit in executed.hits]

    context = _search_to_context(normalized, main_search, executed, results, request)
    context["new_facets"] = aggs_to_context(executed)

    return render(request, "mainapp/search/search.html", context)


def aggs_to_context(executed):
    # TODO: Optimize this to get the names from elasticsearch
    new_facets_context = {}
    org = settings.SITE_DEFAULT_ORGANIZATION
    bucketing = {
        "organization": Organization.objects.all(),
        "person": Person.objects.filter(
            organizationmembership__organization=org
        ).distinct(),
    }
    for aggs_field, queryset in bucketing.items():
        aggs_count = 0
        view_list = []
        for db_object in queryset:
            view_object = {"id": db_object.id, "name": db_object.name, "doc_count": 0}
            setattr(db_object, "doc_count", 0)
            for bucket in executed.facets[aggs_field]:
                if bucket[0] == db_object.id:
                    view_object["doc_count"] = bucket[1]
                    aggs_count += 1
                    break
            view_list.append(view_object)
        new_facets_context[aggs_field] = {"count": aggs_count, "list": view_list}

    searchable_document_types = []
    for doc_type, translated in DOCUMENT_TYPE_NAMES.items():
        for i in executed.facets["document_type"]:
            if i[0] == doc_type + "_document":
                count = i[1]
                break
        else:
            count = 0
        searchable_document_types.append(
            {"name": doc_type, "localized": translated, "count": count}
        )
    new_facets_context["document_type"] = {"list": searchable_document_types}
    return new_facets_context


def search_results_only(request, query):
    """ Returns only the result list items. Used for the endless scrolling """
    params = search_string_to_params(query)
    normalized = params_to_search_string(params)
    after = int(request.GET.get("after", 0))
    main_search = MainappSearch(
        params, offset=after, limit=settings.SEARCH_PAGINATION_LENGTH
    )

    executed = main_search.execute()
    results = [parse_hit(hit) for hit in executed.hits]
    context = _search_to_context(normalized, main_search, executed, results, request)

    result = {
        "results": loader.render_to_string(
            "partials/mixed_results.html", context, request
        ),
        "total_results": executed.hits.total,
        "subscribe_widget": loader.render_to_string(
            "partials/subscribe_widget.html", context, request
        ),
        "more_link": reverse(search_results_only, args=[normalized]),
        # TOOD: Currently we need both because the js for the dropdown facet
        # and document type facet hasn't been unified
        "facets": executed.facets.to_dict(),
        "new_facets": aggs_to_context(executed),
        "query": normalized,
    }

    return JsonResponse(result, safe=False)


def search_autocomplete(_, query):
    if not settings.USE_ELASTICSEARCH:
        results = [{"name": _("search disabled"), "url": reverse("index")}]
        return HttpResponse(json.dumps(results), content_type="application/json")

    # https://www.elastic.co/guide/en/elasticsearch/guide/current/_index_time_search_as_you_type.html
    # We use the ngram-based autocomplete-analyzer for indexing, but the standard analyzer for searching
    # This way we enforce that the whole entered word has to be matched (save for some fuzziness) and the algorithm
    # does not fall back to matching only the first character in extreme cases. This prevents absurd cases where
    # "Garret Walker" and "Hector Mendoza" are suggested when we're entering "Mahatma Ghandi"
    search = (
        Search(index=settings.ELASTICSEARCH_INDEX)
        .query(
            "match",
            autocomplete={
                "query": escape_elasticsearch_query(query),
                "analyzer": "standard",
                "fuzziness": "AUTO",
                "prefix_length": 1,
            },
        )
        .extra(min_score=1)
    )
    response = search.execute()

    multibody = Body.objects.count() > 1

    results = []
    num_persons = num_organizations = 0
    limit_per_type = 5

    for hit in response.hits:
        if hit.meta.doc_type == "person_document":
            if num_persons < limit_per_type:
                results.append(
                    {"name": hit.name, "url": reverse("person", args=[hit.id])}
                )
                num_persons += 1
        elif hit.meta.doc_type == "organization_document":
            if num_organizations < limit_per_type:
                if multibody and hit.body:
                    name = hit.name + " (" + hit.body.name + ")"
                else:
                    name = hit.name
                results.append(
                    {"name": name, "url": reverse("organization", args=[hit.id])}
                )
                num_organizations += 1
        elif hit.meta.doc_type in [
            "file_document",
            "paper_document",
            "meeting_document",
        ]:
            name = hit.name
            results.append(
                {
                    "name": name,
                    "url": reverse(hit.meta.doc_type.split("_")[0], args=[hit.id]),
                }
            )
        else:
            logger.error(
                "Unknown document type in elastic search response: %s"
                % hit.meta.doc_type
            )

    return JsonResponse(results, safe=False)


def search_format_geo(_, lat, lng):
    return JsonResponse(
        {"lat": lat, "lng": lng, "formatted": latlng_to_address(lat, lng)}, safe=False
    )
