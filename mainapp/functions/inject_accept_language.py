from django.conf import settings


def inject_accept_language(get_response):
    """
    https://gist.github.com/vstoykov/1366794?permalink_comment_id=1931322#gistcomment-1931322

    Ignore Accept-Language HTTP headers.

    This will force the I18N machinery to always choose

      - Ukrainian for the main site
      - ADMIN_LANGUAGE_CODE for the admin site

    as the default initial language unless another one is set via
    sessions or cookies.

    Should be installed *before* any middleware that checks
    request.META['HTTP_ACCEPT_LANGUAGE'], namely
    `django.middleware.locale.LocaleMiddleware`.
    """
    admin_lang = getattr(settings, "ADMIN_LANGUAGE_CODE", settings.LANGUAGE_CODE)

    def middleware(request):
        if "HTTP_ACCEPT_LANGUAGE" in request.META:
            del request.META["HTTP_ACCEPT_LANGUAGE"]

        return get_response(request)

    return middleware
