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
from mainapp.functions.search_tools import params_to_query, search_string_to_params, params_are_subscribable, \
    html_escape_highlight, escape_elasticsearch_query
from mainapp.models import Body, Organization, Person
from mainapp.views.utils import handle_subscribe_requests, is_subscribed_to_search, NeedsLoginError
from mainapp.views.views import _build_map_object

logger = logging.getLogger(__name__)


def _parse_hit(hit):
    parsed = hit.__dict__['_d_']  # Extract the raw fields from the hit
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
    else:
        parsed["highlight"] = None
    parsed["name_escaped"] = html_escape_highlight(parsed["name"])
    return parsed


def _search_to_context(query, params: dict, options, results, total_hits, request):
    context = {
        "query": query,
        "results": results,
        "options": options,
        "document_types": DOCUMENT_TYPE_NAMES,
        "map": _build_map_object(Body.objects.get(id=settings.SITE_DEFAULT_BODY), []),
        "pagination_length": settings.SEARCH_PAGINATION_LENGTH,
        "total_hits": total_hits,
        "subscribable": params_are_subscribable(params),
        'is_subscribed': is_subscribed_to_search(request.user, params)
    }

    return context


def _search_to_results(search):
    """ Extracted to allow mocking in tests """
    executed = search.execute()
    results = [_parse_hit(hit) for hit in executed]
    return results, executed.hits.total


@csp_update(STYLE_SRC=("'self'", "'unsafe-inline'"))
def search_index(request, query):
    params = search_string_to_params(query)
    options, search, errors = params_to_query(params)
    for error in errors:
        messages.error(request, error)

    try:
        handle_subscribe_requests(request, params,
                                  _('You will now receive notifications about new search results.'),
                                  _('You will no longer receive notifications.'),
                                  _('You have already subscribed to this search.'))
    except NeedsLoginError as err:
        return redirect(err.redirect_url)

    search = search[:settings.SEARCH_PAGINATION_LENGTH]
    results, total_hits = _search_to_results(search)
    context = _search_to_context(query, params, options, results, total_hits, request)

    context['searchable_organizations'] = Organization.objects.all()
    org = settings.SITE_DEFAULT_ORGANIZATION
    context['searchable_persons'] = Person.objects.filter(organizationmembership__organization=org).distinct()

    return render(request, "mainapp/search/search.html", context)


def search_results_only(request, query):
    """ Returns only the result list items. Used for the endless scrolling """
    params = search_string_to_params(query)
    options, search, _ = params_to_query(params)
    after = int(request.GET.get('after', 0))
    search = search[after:][:settings.SEARCH_PAGINATION_LENGTH]
    results, total_hits = _search_to_results(search)
    context = _search_to_context(query, params, options, results, total_hits, request)

    result = {
        'results': loader.render_to_string('partials/mixed_results.html', context, request),
        'total_results': total_hits,
        'subscribe_widget': loader.render_to_string('partials/subscribe_widget.html', context, request),
        'more_link': reverse(search_results_only, args=[query]),
    }

    return JsonResponse(result, safe=False)


def search_autosuggest(_, query):
    if not settings.USE_ELASTICSEARCH:
        results = [{'name': _('search disabled'), 'url': reverse('index')}]
        return HttpResponse(json.dumps(results), content_type='application/json')

    # https://www.elastic.co/guide/en/elasticsearch/guide/current/_index_time_search_as_you_type.html
    # We use the ngram-based autocomplete-analyzer for indexing, but the standard analyzer for searching
    # This way we enforce that the whole entered word has to be matched (save for some fuzziness) and the algorithm
    # does not fall back to matching only the first character in extreme cases. This prevents absurd cases where
    # "Garret Walker" and "Hector Mendoza" are suggested when we're entering "Mahatma Ghandi"
    search = Search(index=settings.ELASTICSEARCH_INDEX).query("match", autocomplete={
        'query': escape_elasticsearch_query(query),
        'analyzer': 'standard',
        'fuzziness': 'AUTO',
        'prefix_length': 1
    }).extra(min_score=1)
    response = search.execute()

    multibody = Body.objects.count() > 1

    results = []
    num_persons = num_organizations = 0
    limit_per_type = 5

    for hit in response.hits:
        if hit.meta.doc_type == 'person_document':
            if num_persons < limit_per_type:
                results.append({'name': hit.name, 'url': reverse('person', args=[hit.id])})
                num_persons += 1
        elif hit.meta.doc_type == 'organization_document':
            if num_organizations < limit_per_type:
                if multibody and hit.body:
                    name = hit.name + " (" + hit.body.name + ")"
                else:
                    name = hit.name
                results.append({'name': name, 'url': reverse('organization', args=[hit.id])})
                num_organizations += 1
        elif hit.meta.doc_type == 'paper_document':
            name = hit.name
            results.append({'name': name, 'url': reverse('paper', args=[hit.id])})
        elif hit.meta.doc_type == 'meeting_document':
            name = hit.name
            results.append({'name': name, 'url': reverse('meeting', args=[hit.id])})
        else:
            logger.error("Unknown document type in elastic search response: %s" % hit.meta.doc_type)

    return JsonResponse(results, safe=False)


def search_format_geo(_, lat, lng):
    return JsonResponse({
        "lat": lat,
        "lng": lng,
        "formatted": latlng_to_address(lat, lng)
    }, safe=False)
