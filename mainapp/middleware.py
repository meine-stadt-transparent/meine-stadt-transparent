from django.urls import resolve
from django.utils.deprecation import MiddlewareMixin
from django.conf import settings


class CSPMiddleware(MiddlewareMixin):
    def process_response(self, request, response):
        current_url = resolve(request.path_info).url_name

        if settings.SOCIALACCOUNT_USE_FACEBOOK and current_url == 'account_login':
            response._csp_update = {
                'img-src': "www.facebook.com web.facebook.com",
                'script-src': "connect.facebook.net 'unsafe-eval' 'unsafe-inline'",
                'style-src': "*.facebook.com *.facebook.net 'unsafe-inline'",
                'frame-src': "*.facebook.com"
            }

        return response
