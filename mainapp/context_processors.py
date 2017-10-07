from django.conf import settings


def seo(request):
    if settings.SITE_SEO_NOINDEX:
        robots_index = 'noindex'
    else:
        robots_index = 'index'

    return {
        'seo_robotos_index': robots_index
    }
