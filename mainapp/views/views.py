import json

from csp.decorators import csp_update
from django.conf import settings
from django.conf.urls.static import static
from django.db.models import Q, Count
from django.shortcuts import render, get_object_or_404
from django.templatetags.static import static
from django.urls import reverse
from django.utils import html
from django.utils import timezone
from django.views.generic import DetailView
from django.views.static import serve
from requests.utils import quote

from mainapp.documents import DOCUMENT_TYPE_NAMES, DOCUMENT_TYPE_NAMES_PL
from mainapp.functions.document_parsing import index_papers_to_geodata
from mainapp.models import Body, File, Organization, Paper, Meeting, Person, LegislativeTerm, \
    Location
from mainapp.models.organization import ORGANIZATION_TYPE_NAMES_PLURAL
from mainapp.models.organization_type import OrganizationType
from mainapp.views import person_grid_context


def index(request):
    main_body = Body.objects.get(id=settings.SITE_DEFAULT_BODY)

    latest_paper = Paper.objects.order_by("-sort_date", "-legal_date")[:10]
    for paper in latest_paper:
        # The mixed results view needs those
        setattr(paper, "type", "paper")
        setattr(paper, "name_escaped", html.escape(paper.name))
        setattr(paper, "type_translated", DOCUMENT_TYPE_NAMES[paper.type])
        setattr(paper, "url", paper.get_default_link())

    geo_papers = Paper \
                     .objects \
                     .order_by("-sort_date", "-legal_date") \
                     .prefetch_related('files') \
                     .prefetch_related('files__locations')[:50]

    stats = {
        "file": File.objects.count(),
        "meeting": Meeting.objects.count(),
        "organization": Organization.objects.count(),
        "paper": Paper.objects.count(),
        "person": Person.objects.count()
    }

    context = {
        'map': _build_map_object(main_body, geo_papers),
        'latest_paper': latest_paper,
        'next_meetings': Meeting.objects.filter(start__gt=timezone.now()).order_by("start")[:2],
        'stats': stats
    }

    if request.GET.get('version', 'v2') == 'v2':
        return render(request, 'mainapp/index_v2/index.html', context)
    else:
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
        ct1 = Count('organizationmembership', distinct=True)
        ct2 = Count('paper', distinct=True)
        ct3 = Count('meeting', distinct=True)
        all_orgas = Organization.objects.annotate(ct1, ct2, ct3).filter(
            organization_type=organization_type).all()

        organizations_ordered.append({
            "organization_type": organization_type,
            "type": ORGANIZATION_TYPE_NAMES_PLURAL.get(organization_type.name,
                                                       organization_type.name),
            "all": all_orgas,
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
        "consultations": [],  # Blocked by #63
    }
    return render(request, "mainapp/paper.html", context)


def organization(request, pk):
    organization = get_object_or_404(Organization, id=pk)

    members, parliamentarygroups = person_grid_context(organization)

    context = {
        "members": members,
        "parliamentary_groups": parliamentarygroups,
        "organization": organization,
        "papers": Paper.objects.filter(organizations__in=[pk])
                      .order_by('legal_date', 'modified')[:25],
        "paper_count": Paper.objects.filter(organizations__in=[pk]).count(),
        "meetings": Meeting.objects.filter(organizations__in=[pk])
                        .order_by('-start', 'modified')[:25],
        "meeting_count": Meeting.objects.filter(organizations__in=[pk]).count(),
        "to_search_url": reverse("search", args=["organization:" + str(organization.id)])
    }
    return render(request, "mainapp/organization.html", context)


@csp_update(FRAME_SRC=("'self'", "blob:"))  # Needed for downloading the PDF in PDF.JS
def file(request, pk):
    file = get_object_or_404(File, id=pk)

    renderer = "download"

    if file.mime_type == "application/pdf":
        renderer = "pdf"
    elif file.mime_type == "text/plain":
        renderer = "txt"
    elif file.mime_type in ["image/gif", "image/jpg", "image/jpeg", "image/png", "image/webp"]:
        renderer = "image"

    if not (file.filesize and file.filesize > 0):
        renderer = None

    context = {
        "file": file,
        "papers": Paper.objects.filter(Q(files__in=[file]) | Q(main_file=file)).distinct(),
        "renderer": renderer,
    }

    if renderer == "pdf":
        context["pdfjs_iframe_url"] = static('vendored/web/viewer.html')
        context["pdfjs_iframe_url"] += "?file=" + reverse('media', args=[file.storage_filename])
        if request.GET.get("pdfjs_search"):
            context["pdfjs_iframe_url"] += "#search=" + quote(request.GET.get("pdfjs_search"))
            if request.GET.get("pdfjs_phrase"):
                context["pdfjs_iframe_url"] += "&phrase=" + quote(request.GET.get("pdfjs_phrase"))

    return render(request, "mainapp/file/file.html", context)


def file_serve(request, path):
    file_object = get_object_or_404(File, storage_filename=path)

    response = serve(request, path, document_root=settings.MEDIA_ROOT, show_indexes=False)
    response['Content-Type'] = file_object.mime_type
    response['Content-Disposition'] = "attachment; filename=" + file_object.displayed_filename
    if settings.SITE_SEO_NOINDEX:
        response['X-Robots-Tag'] = 'noindex'

    return response


def info_privacy(request):
    return render(request, 'info/privacy.html', {
        "use_facebook": settings.SOCIALACCOUNT_USE_FACEBOOK,
        "use_twitter": settings.SOCIALACCOUNT_USE_TWITTER,
    })


def info_contact(request):
    return render(request, 'info/contact.html', {})


def info_feedback(request):
    return render(request, 'info/feedback.html', {})


def info_about(request):
    context = {
        "stats": {
            DOCUMENT_TYPE_NAMES_PL["file"]: File.objects.count(),
            DOCUMENT_TYPE_NAMES_PL["meeting"]: Meeting.objects.count(),
            DOCUMENT_TYPE_NAMES_PL["organization"]: Organization.objects.count(),
            DOCUMENT_TYPE_NAMES_PL["paper"]: Paper.objects.count(),
            DOCUMENT_TYPE_NAMES_PL["person"]: Person.objects.count(),
        }
    }

    return render(request, 'info/about.html', context)


def error404(request):
    return render(request, "error/404.html", status=404)


def error500(request):
    return render(request, "error/500.html", status=500)


def body(request, pk):
    body = get_object_or_404(Body, id=pk)
    context = {
        'body': body,
        'map': _build_map_object(body, []),
    }
    return render(request, "mainapp/body.html", context)


legislative_term = DetailView.as_view(model=LegislativeTerm,
                                      template_name="mainapp/legislative_term.html")
location = DetailView.as_view(model=Location, template_name="mainapp/location.html")
