from django.conf import settings


def seo(_request):
    if settings.SITE_SEO_NOINDEX:
        robots_index = "noindex"
    else:
        robots_index = "index"

    return {"seo_robots_index": robots_index}
