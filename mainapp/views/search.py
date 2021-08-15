import json
import logging

from csp.decorators import csp_update
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect
from django.template import loader
from django.urls import reverse
from django.utils.translation import gettext as _

from mainapp.functions.geo_functions import latlng_to_address
from mainapp.functions.search import (
    search_string_to_params,
    MainappSearch,
    parse_hit,
    params_to_search_string,
    DOCUMENT_TYPE_NAMES,
    autocomplete,
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
    assert executed.hits.total["relation"] in ["eq", "gte"]

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
    new_facets_context = {}
    org = settings.SITE_DEFAULT_ORGANIZATION
    bucketing = {
        "organization": Organization.objects.all(),
        "person": Person.objects.filter(membership__organization=org).distinct(),
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
            if i[0] == settings.ELASTICSEARCH_PREFIX + "-" + doc_type:
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
    """Returns only the result list items. Used for the endless scrolling"""
    params = search_string_to_params(query)
    normalized = params_to_search_string(params)
    after = int(request.GET.get("after", 0))
    main_search = MainappSearch(
        params, offset=after, limit=settings.SEARCH_PAGINATION_LENGTH
    )

    executed = main_search.execute()
    # The mocked results don't have a took value
    logger.debug("Elasticsearch query took {}ms".format(executed.to_dict().get("took")))
    results = [parse_hit(hit) for hit in executed.hits]
    context = _search_to_context(normalized, main_search, executed, results, request)

    assert executed.hits.total["relation"] in ["eq", "gte"]

    total_results = executed.hits.total
    if not isinstance(total_results, dict):
        total_results = total_results.to_dict()

    result = {
        "results": loader.render_to_string(
            "mainapp/search/results_section.html", context, request
        ),
        "total_results": total_results,
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
    if not settings.ELASTICSEARCH_ENABLED:
        results = [{"name": _("search disabled"), "url": reverse("index")}]
        return HttpResponse(json.dumps(results), content_type="application/json")

    response = autocomplete(query)

    multibody = Body.objects.count() > 1

    results = []
    num_persons = num_organizations = 0
    limit_per_type = 5

    for hit in response.hits:
        doc_type = hit.meta.index.split("-")[-1]
        if doc_type == "person":
            if num_persons < limit_per_type:
                results.append(
                    {"name": hit.name, "url": reverse("person", args=[hit.id])}
                )
                num_persons += 1
        elif doc_type == "organization":
            if num_organizations < limit_per_type:
                if multibody and hit.body:
                    name = hit.name + " (" + hit.body.name + ")"
                else:
                    name = hit.name
                results.append(
                    {"name": name, "url": reverse("organization", args=[hit.id])}
                )
                num_organizations += 1
        elif doc_type in ["file", "paper", "meeting"]:
            name = hit.name
            results.append({"name": name, "url": reverse(doc_type, args=[hit.id])})
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
