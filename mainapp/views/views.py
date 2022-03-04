import logging
from datetime import timedelta
from os.path import splitext
from urllib.parse import quote, urlparse

from csp.decorators import csp_update
from django.conf import settings
from django.db.models import Q, Count
from django.http import HttpRequest, StreamingHttpResponse, HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.templatetags.static import static
from django.urls import reverse
from django.utils import html
from django.utils import timezone
from django.views.generic import DetailView

from importer.functions import requests_get
from mainapp.functions.minio import minio_client, minio_file_bucket
from mainapp.functions.search import DOCUMENT_TYPE_NAMES_PL
from mainapp.models import (
    Body,
    File,
    Organization,
    Paper,
    Meeting,
    Person,
    LegislativeTerm,
    Location,
)
from mainapp.models.organization import ORGANIZATION_TYPE_NAMES_PLURAL
from mainapp.models.organization_type import OrganizationType
from mainapp.views import person_grid_context, HttpResponse, DOCUMENT_TYPE_NAMES
from mainapp.views.utils import build_map_object

logger = logging.getLogger(__name__)


def index(request):
    main_body = Body.objects.filter(pk=settings.SITE_DEFAULT_BODY).first()

    if not main_body:
        if Body.objects.count() == 0:
            return render(request, "mainapp/installation_successful.html")
        else:
            context = {
                "site_default_body": settings.SITE_DEFAULT_BODY,
                "bodies": Body.objects.all(),
            }
            return render(request, "mainapp/default_body_missing.html", context)

    latest_paper = Paper.objects.order_by("-sort_date")[:10]
    for paper in latest_paper:
        # The mixed results view needs those
        setattr(paper, "type", "paper")
        setattr(paper, "name_escaped", html.escape(paper.name))
        setattr(paper, "type_translated", DOCUMENT_TYPE_NAMES[paper.type])
        setattr(paper, "url", paper.get_default_link())

    geo_papers = (
        Paper.objects.order_by("-sort_date")
        .prefetch_related("main_file")
        .prefetch_related("main_file__locations")
        .prefetch_related("files")
        .prefetch_related("files__locations")[:50]
    )

    stats = {
        "file": File.objects.count(),
        "meeting": Meeting.objects.count(),
        "organization": Organization.objects.count(),
        "paper": Paper.objects.count(),
        "person": Person.objects.count(),
    }

    map_object = build_map_object(main_body, geo_papers)

    context = {
        "map": map_object,
        "latest_paper": latest_paper,
        "next_meetings": Meeting.objects.filter(start__gt=timezone.now()).order_by(
            "start"
        )[:2],
        "stats": stats,
        "body_name": main_body.short_name,
    }

    if request.GET.get("version", "v2") == "v2":
        return render(request, "mainapp/index_v2/index.html", context)
    else:
        return render(request, "mainapp/index/index.html", context)


def organizations(request):
    organizations_ordered = []
    for organization_type in OrganizationType.objects.all():
        ct1 = Count("membership", distinct=True)
        ct2 = Count("paper", distinct=True)
        ct3 = Count("meeting", distinct=True)
        all_orgas = list(
            Organization.objects.annotate(ct1, ct2, ct3)
            .filter(organization_type=organization_type)
            .all()
        )

        organizations_ordered.append(
            {
                "organization_type": organization_type,
                "type": ORGANIZATION_TYPE_NAMES_PLURAL.get(
                    organization_type.name, organization_type.name
                ),
                "all": all_orgas,
            }
        )

    for i in settings.ORGANIZATION_ORDER:
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
    context = {"paper": paper, "consultations": paper.consultation_set.all()}
    return render(request, "mainapp/paper.html", context)


def historical_paper(request, pk):
    historical_paper = get_object_or_404(Paper.history, history_id=pk)
    context = {
        "paper": historical_paper.instance,
        "historical": historical_paper,
        "consultations": [],  # Blocked by #63
        "seo_robots_index": "noindex",
    }
    return render(request, "mainapp/paper.html", context)


def organization(request, pk):
    organization = get_object_or_404(Organization, id=pk)

    members, parliamentarygroups = person_grid_context(organization)

    context = {
        "members": members,
        "parliamentary_groups": parliamentarygroups,
        "organization": organization,
        "papers": Paper.objects.filter(organizations__in=[pk]).order_by(
            "-legal_date", "modified"
        )[:25],
        "paper_count": Paper.objects.filter(organizations__in=[pk]).count(),
        "meetings": Meeting.objects.filter(organizations__in=[pk]).order_by(
            "-start", "modified"
        )[:25],
        "meeting_count": Meeting.objects.filter(organizations__in=[pk]).count(),
        "to_search_url": reverse(
            "search", args=["organization:" + str(organization.id)]
        ),
    }
    return render(request, "mainapp/organization.html", context)


@csp_update(FRAME_SRC=("'self'", "blob:"))  # Needed for downloading the PDF in PDF.JS
def file(request, pk, context_meeting_id=None):
    file = get_object_or_404(File, id=pk)
    if context_meeting_id:
        context_meeting = get_object_or_404(Meeting, id=context_meeting_id)
    else:
        context_meeting = None

    renderer = "download"

    if file.mime_type == "application/pdf" or file.mime_type.startswith(
        "application/pdf;"
    ):
        renderer = "pdf"
    elif file.mime_type == "text/plain":
        renderer = "txt"
    elif file.mime_type in [
        "image/gif",
        "image/jpg",
        "image/jpeg",
        "image/png",
        "image/webp",
    ]:
        renderer = "image"

    if not file.filesize:
        renderer = None
        if settings.PROXY_ONLY_TEMPLATE:
            renderer = "pdf"

    context = {
        "file": file,
        "papers": Paper.objects.filter(
            Q(files__in=[file]) | Q(main_file=file)
        ).distinct(),
        "renderer": renderer,
        "pdf_parsed_text": settings.EMBED_PARSED_TEXT_FOR_SCREENREADERS,
        "context_meeting": context_meeting,
    }

    if renderer == "pdf":
        context["pdfjs_iframe_url"] = static("web/viewer.html")
        if settings.PROXY_ONLY_TEMPLATE:
            file_url = reverse("file-content-proxy", args=[int(file.oparl_id)])
        else:
            file_url = reverse("file-content", args=[file.id])
        context["pdfjs_iframe_url"] += "?file=" + file_url
        if request.GET.get("pdfjs_search"):
            context["pdfjs_iframe_url"] += "#search=" + quote(
                request.GET.get("pdfjs_search")
            )
            if request.GET.get("pdfjs_phrase"):
                context["pdfjs_iframe_url"] += "&phrase=" + quote(
                    request.GET.get("pdfjs_phrase")
                )

    return render(request, "mainapp/file/file.html", context)


def file_serve_proxy(request: HttpRequest, pk: int) -> StreamingHttpResponse:
    """Util to proxy back to the original RIS in case we don't want to download all the files"""
    # Ensure that the file is not deleted in the database
    get_object_or_404(File, pk=pk)

    url = settings.PROXY_ONLY_TEMPLATE.format(pk)

    response = requests_get(url, stream=True)
    return StreamingHttpResponse(
        response.iter_content(chunk_size=None), status=response.status_code
    )


def file_serve(request, id):
    """Ensure that the file is not deleted in the database"""
    file = get_object_or_404(File, id=id)

    name, ext = splitext(file.filename)
    if name.isnumeric() and file.name and len(file.name) < 50:
        filename = f"{file.name}_{name}{ext}"
    else:
        filename = file.filename

    filename_safe = filename.encode("ascii", "ignore")

    headers = {
        # Encoding according to RFC5987
        "Content-Disposition": f"attachment; filename=\"{quote(filename_safe)}\"; filename*=UTF-8''{quote(filename)}",
        "Content-Type": str(file.mime_type),
    }

    if settings.SITE_SEO_NOINDEX:
        headers["X-Robots-Tag"] = "noindex"

    if settings.MINIO_REDIRECT:
        public = settings.MINIO_PUBLIC_HOST is not None
        url = minio_client(public).presigned_get_object(
            minio_file_bucket,
            str(id),
            expires=timedelta(hours=2),
            response_headers=headers,
        )

        minio_url = urlparse(url)

        response = HttpResponseRedirect(minio_url.geturl())

    else:
        logger.warning("Serving media files through django is slow")

        minio_file = minio_client().get_object(minio_file_bucket, str(id))

        response = HttpResponse(minio_file.read(), headers=headers)

    return response


def info_privacy(request):
    return render(
        request,
        "info/privacy.html",
        {
            "use_facebook": settings.SOCIALACCOUNT_USE_FACEBOOK,
            "use_twitter": settings.SOCIALACCOUNT_USE_TWITTER,
            "seo_robots_index": "noindex",
        },
    )


def info_contact(request):
    return render(request, "info/contact.html", {"seo_robots_index": "noindex"})


def info_feedback(request):
    return render(request, "info/feedback.html", {"seo_robots_index": "noindex"})


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

    return render(request, "info/about.html", context)


def body(request, pk):
    body = get_object_or_404(Body, id=pk)
    context = {"body": body, "map": build_map_object(body)}
    return render(request, "mainapp/body.html", context)


legislative_term = DetailView.as_view(
    model=LegislativeTerm, template_name="mainapp/legislative_term.html"
)
location = DetailView.as_view(model=Location, template_name="mainapp/location.html")
