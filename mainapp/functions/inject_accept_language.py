def inject_accept_language(get_response):
    """
    https://gist.github.com/vstoykov/1366794?permalink_comment_id=1931322#gistcomment-1931322

    Ignore Accept-Language HTTP headers, so that we always have German for the main site unless the user picked
    something different
    """

    def middleware(request):
        if "HTTP_ACCEPT_LANGUAGE" in request.META:
            del request.META["HTTP_ACCEPT_LANGUAGE"]

        return get_response(request)

    return middleware
