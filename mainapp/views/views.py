import json

from django.conf import settings
from django.db.models import Q
from django.shortcuts import render, get_object_or_404
from django.utils import html

from mainapp.documents import DOCUMENT_TYPE_NAMES
from mainapp.functions.document_parsing import index_papers_to_geodata
from mainapp.models import Body, File, Consultation, Organization, Paper, Meeting, Person
from mainapp.models.organization import ORGANIZATION_TYPE_NAMES
from mainapp.models.organization_type import OrganizationType


def index(request):
    main_body = Body.objects.get(id=settings.SITE_DEFAULT_BODY)

    latest_paper = Paper.objects.order_by("-modified", "-legal_date")[:10]
    for paper in latest_paper:
        # The mixed results view needs those
        setattr(paper, "type", "paper")
        setattr(paper, "name_escaped", html.escape(paper.name))
        setattr(paper, "type_translated", DOCUMENT_TYPE_NAMES[paper.type])

    geo_papers = Paper \
                     .objects \
                     .order_by("-modified", "-legal_date") \
                     .prefetch_related('files') \
                     .prefetch_related('files__locations')[:50]

    context = {
        'map': _build_map_object(main_body, geo_papers),
        'latest_paper': latest_paper,
    }
    return render(request, 'mainapp/index/index.html', context)


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
    organizations_ordered = []
    for organization_type in OrganizationType.objects.all():
        organizations_ordered.append({
            "organization_type": organization_type,
            "type": ORGANIZATION_TYPE_NAMES.get(organization_type.name, organization_type.name),
            "all": Organization.objects.filter(organization_type=organization_type).all(),
        })

    for i in settings.ORGANIZATION_TYPE_SORTING:
        j = 0
        while j < len(organizations_ordered):
            if organizations_ordered[j]["organization_type"].id == i:
                popped = organizations_ordered.pop(j)
                organizations_ordered.insert(0, popped)
            j += 1

    context = {
        "organizations": organizations_ordered,
        "main_organization": settings.SITE_DEFAULT_ORGANIZATION,
    }
    return render(request, "mainapp/organizations.html", context)


def paper(request, pk):
    paper = get_object_or_404(Paper, id=pk)
    context = {
        "paper": paper,
        "consultations": paper.consultation_set.all(),
    }
    return render(request, "mainapp/paper.html", context)


def historical_paper(request, pk):
    historical_paper = get_object_or_404(Paper.history, history_id=pk)
    context = {
        "paper": historical_paper.instance,
        "historical": historical_paper,
        "consultations": [],  # TODO,
    }
    return render(request, "mainapp/paper.html", context)


def organization(request, pk):
    organization = get_object_or_404(Organization, id=pk)
    context = {
        "organization": organization,
        "memberships": Person.objects.filter(organizationmembership__organization_id=pk),
        "papers": Paper.objects.filter(organizations__in=[pk]).order_by('legal_date', 'modified')[:25],
        "meetings": Meeting.objects.filter(organizations__in=[pk]).order_by('start', 'modified')[:25],
    }
    return render(request, "mainapp/organization.html", context)


def file(request, pk):
    file = get_object_or_404(File, id=pk)
    is_available = file.filesize and file.filesize > 0
    renderer = None
    if file.mime_type == "application/pdf":
        renderer = "pdf"
    elif file.mime_type == "text/plain":
        renderer = "txt"
    elif file.mime_type in ["image/gif", "image/jpg", "image/jpeg", "image/png", "image/webp"]:
        renderer = "image"

    context = {
        "file": file,
        "papers": Paper.objects.filter(Q(files__in=[file]) | Q(main_file=file)).distinct(),
        "is_available": is_available,
        "renderer": renderer,
    }
    return render(request, "mainapp/file.html", context)


def info_privacy(request):
    return render(request, 'info/privacy.html', {
        "use_facebook": settings.SOCIALACCOUNT_USE_FACEBOOK,
        "use_twitter": settings.SOCIALACCOUNT_USE_TWITTER,
    })


def info_contact(request):
    return render(request, 'info/contact.html', {})


def info_feedback(request):
    return render(request, 'info/feedback.html', {})


def info_learn(request):
    return render(request, 'info/learn.html', {})


def info_about(request):
    return render(request, 'info/about.html', {})


def error404(request):
    return render(request, "error/404.html", status=404)


def error500(request):
    return render(request, "error/500.html", status=500)
