import json
from datetime import date, timedelta

from django.conf import settings
from django.db.models import Q
from django.shortcuts import render

from mainapp.documents import DOCUMENT_TYPE_NAMES
from mainapp.functions.document_parsing import index_papers_to_geodata
from mainapp.models import Body, Department, Committee, AgendaItem, Meeting, File
from mainapp.models.paper import Paper
from mainapp.models.parliamentary_group import ParliamentaryGroup


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
        'documents': index_papers_to_geodata(geo_papers),
        'mapboxKey': settings.SITE_MAPBOX_ACCESS_TOKEN,
        'tileUrl': settings.SITE_MAPBOX_TILE_URL,
    })


def organizations(request):
    context = {
        "committees": Committee.objects.all(),
        "departments": Department.objects.all(),
        "organizations": [],  # TODO
        "parliamentary_groups": ParliamentaryGroup.objects.all(),
    }
    return render(request, "mainapp/organizations.html", context)


def paper(request, pk):
    context = {
        "paper": Paper.objects.get(id=pk),
        "history": AgendaItem.objects.filter(paper_id=pk).all(),
    }
    return render(request, "mainapp/paper.html", context)


def department(request, pk):
    organization = Department.objects.get(id=pk)
    context = {
        "organization": organization,
        "memberships": organization.departmentmembership_set.all(),
        "papers": Paper.objects.filter(submitter_departments__in=pk)[:25],
    }
    return render(request, "mainapp/department.html", context)


def committee(request, pk):
    organization = Committee.objects.get(id=pk)
    context = {
        "organization": organization,
        "memberships": organization.committeemembership_set.all(),
        "papers": Paper.objects.filter(submitter_committees__in=pk)[:25],
        "meetings": Meeting.objects.filter(committees__in=pk)[:25],
    }
    return render(request, "mainapp/committee.html", context)


def parliamentary_group(request, pk):
    organization = ParliamentaryGroup.objects.get(id=pk)
    context = {
        "organization": organization,
        "memberships": organization.parliamentarygroupmembership_set.all(),
        "papers": Paper.objects.filter(submitter_parliamentary_groups__in=pk)[:25],
    }
    return render(request, "mainapp/parliamentary_group.html", context)


def file(request, pk):
    file = File.objects.get(id=pk)
    is_available = file.filesize and file.filesize > 0
    context = {
        "file": file,
        "papers": Paper.objects.filter(Q(files__in=[file]) | Q(main_file=file)).distinct(),
        "is_available": is_available,
        "is_renderable": is_available and file.mime_type == "application/pdf",
    }
    return render(request, "mainapp/file.html", context)


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
