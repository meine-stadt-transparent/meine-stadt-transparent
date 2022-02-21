"""
Views that are special in that they normally shouldn't be user-facing
"""

from html import escape

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils.translation import gettext as _

from mainapp.models import Paper, Meeting, Person, Body


def robots_txt(_request):
    if settings.SITE_SEO_NOINDEX:
        return HttpResponse("User-agent: *\nDisallow: /", content_type="text/plain")
    else:
        sitemap_url = settings.ABSOLUTE_URI_BASE + reverse("sitemap-xml")
        return HttpResponse(
            "User-agent: *\nDisallow: /accounts/\nSitemap: " + sitemap_url,
            content_type="text/plain",
        )


def sitemap_xml_entry(obj, priority):
    return f""""<url>
  <loc>{settings.ABSOLUTE_URI_BASE}{obj.get_default_link()}</loc>
  <lastmod>{obj.modified.strftime("%Y-%m-%d")}</lastmod>
  <changefreq>weekly</changefreq>
  <priority>{priority}</priority>
</url>
"""


def sitemap_xml(_request):
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        + "\n"
    )

    for paper_obj in Paper.objects.all():
        xml += sitemap_xml_entry(paper_obj, 0.8)

    for meet_obj in Meeting.objects.all():
        xml += sitemap_xml_entry(meet_obj, 0.9)

    for person_obj in Person.objects.all():
        xml += sitemap_xml_entry(person_obj, 0.9)

    xml += "</urlset>"
    return HttpResponse(xml, content_type="application/xml")


def opensearch_xml(_request):
    main_body = Body.objects.get(id=settings.SITE_DEFAULT_BODY)
    description = _("Search for documents of %CITY%'s city council").replace(
        "%CITY%", main_body.short_name
    )
    url = settings.ABSOLUTE_URI_BASE + "/search/query/{searchTerms}/"
    xml = (
        '<OpenSearchDescription xmlns="http://a9.com/-/spec/opensearch/1.1/" '
        'xmlns:moz="http://www.mozilla.org/2006/browser/search/">'
        "<ShortName>" + escape(settings.TEMPLATE_META["site_name"]) + "</ShortName>"
        "<Description>" + escape(description) + "</Description>"
        "<InputEncoding>UTF-8</InputEncoding>"
        '<Url type="text/html" method="get" template="' + escape(url) + '"/>'
        "<moz:SearchForm>" + settings.ABSOLUTE_URI_BASE + "</moz:SearchForm>"
        "</OpenSearchDescription>"
    )
    return HttpResponse(xml, content_type="application/opensearchdescription+xml")


# noinspection PyUnusedLocal
def error404(request, *args, **kwargs):
    return render(request, "error/404.html", status=404)


# noinspection PyUnusedLocal
def error500(request, *args, **kwargs):
    return render(request, "error/500.html", status=500)
