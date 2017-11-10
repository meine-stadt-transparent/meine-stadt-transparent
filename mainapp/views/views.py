import json
from datetime import date, timedelta

from django.conf import settings
from django.shortcuts import render

from mainapp.documents import DOCUMENT_TYPE_NAMES
from mainapp.functions.document_parsing import index_papers_to_geodata
from mainapp.models import Body, Department, Committee
from mainapp.models.paper import Paper


def index(request):
    main_body = Body.objects.get(id=settings.SITE_DEFAULT_BODY)

    document_end_date = date.today() + timedelta(days=1)
    document_start_date = document_end_date - timedelta(days=settings.SITE_INDEX_DOCUMENT_DAY)
    latest_paper = Paper \
                       .objects \
                       .filter(modified__range=[document_start_date, document_end_date]) \
                       .order_by("-modified", "-legal_date")[:10]
    for paper in latest_paper:
        # The mixed results view needs those
        setattr(paper, "type", "paper")
        setattr(paper, "type_translated", DOCUMENT_TYPE_NAMES[paper.type])

    geo_papers = Paper \
                     .objects \
                     .filter(modified__range=[document_start_date, document_end_date]) \
                     .prefetch_related('files') \
                     .prefetch_related('files__locations')[:50]

    context = {
        'map': _build_map_object(main_body, geo_papers),
        'latest_paper': latest_paper,
    }
    return render(request, 'mainapp/index.html', context)


def _build_map_object(body: Body, geo_papers):
    if body.outline:
        outline = body.outline.geometry
    else:
        outline = None

    return json.dumps({
        'center': settings.SITE_GEO_CENTER,
        'zoom': settings.SITE_GEO_INIT_ZOOM,
        'limit': settings.SITE_GEO_LIMITS,
        'outline': outline,
        'documents': index_papers_to_geodata(geo_papers)
    })


def info_privacy(request):
    return render(request, 'info/privacy.html', {})


def info_contact(request):
    return render(request, 'info/contact.html', {})


def info_about(request):
    return render(request, 'info/about.html', {})


def error404(request):
    return render(request, "error/404.html", status=404)


def error500(request):
    return render(request, "error/500.html", status=500)


def organizations(request):
    context = {
        "departments": Department.objects.all(),
        "committees": Committee.objects.all(),
        "organizations": [],  # TODO
    }
    return render(request, "mainapp/organizations.html", context)