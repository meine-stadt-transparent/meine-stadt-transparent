import json

from csp.decorators import csp_update
from django.conf import settings
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import ugettext as _
from elasticsearch_dsl import Search

from mainapp.documents import DOCUMENT_TYPE_NAMES
from mainapp.functions.search_tools import params_to_query, search_string_to_params
from mainapp.models import Body
from mainapp.views.views import _build_map_object


def _search_to_context(query, options, s):
    main_body = Body.objects.get(id=settings.SITE_DEFAULT_BODY)

    results = []
    executed = s.execute()
    for hit in executed:
        result = hit.__dict__['_d_']  # Extract the raw fields from the hit
        result["type"] = hit.meta.doc_type.replace("_document", "").replace("_", "-")
        result["type_translated"] = DOCUMENT_TYPE_NAMES[result["type"]]

        if hasattr(hit.meta, "highlight"):
            result["highlight"] = hit.meta.highlight.parsed_text
        results.append(result)

    context = {
        "query": query,
        "results": results,
        "options": options,
        "document_types": DOCUMENT_TYPE_NAMES,
        "map": _build_map_object(main_body, []),
        "total_hits": executed.hits.total,
    }

    return context


@csp_update(STYLE_SRC=("'self'", "'unsafe-inline'"))
def search(request, query):
    options, s, errors = params_to_query(search_string_to_params(query))
    for error in errors:
        messages.error(request, error)
    context = _search_to_context(query, options, s)
    return render(request, "mainapp/search.html", context)


def search_results_only(request, query):
    """ Returns only the result list items. Used for the endless scrolling """
    options, s, _ = params_to_query(search_string_to_params(query))
    after = int(request.GET.get("after"), 0)
    s = s[after:after + 3]
    context = _search_to_context(query, options, s)
    return render(request, "partials/mixed_results.html", context)


def search_autosuggest(request, query):
    if not settings.USE_ELASTICSEARCH:
        results = [{'name': _('search disabled'), 'url': reverse('index')}]
        return HttpResponse(json.dumps(results), content_type='application/json')

    response = Search(index='ris_files').query("match", autocomplete=query).execute()

    bodies = Body.objects.count()

    results = []
    num_persons = num_parliamentary_groups = 0
    limit_per_type = 5

    for hit in response.hits:
        if hit.meta.doc_type == 'person_document':
            if num_persons < limit_per_type:
                results.append({'name': hit.name, 'url': reverse('person', args=[hit.id])})
                num_persons += 1
        elif hit.meta.doc_type == 'parliamentary_group_document':
            if num_parliamentary_groups < limit_per_type:
                if bodies > 1:
                    name = hit.name + " (" + hit.body.name + ")"
                else:
                    name = hit.name
                results.append({'name': name, 'url': reverse('parliamentary-group', args=[hit.id])})
                num_parliamentary_groups += 1
        elif hit.meta.doc_type == 'committee_document':
            name = hit.name
            results.append({'name': name, 'url': reverse('committee', args=[hit.id])})
        elif hit.meta.doc_type == 'paper_document':
            name = hit.name
            results.append({'name': name, 'url': reverse('paper', args=[hit.id])})
        else:
            print("Unknown type: %s" % hit.meta.doc_type)

    return JsonResponse(results, safe=False)