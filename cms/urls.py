from csp.decorators import csp_exempt
from decorator_include import decorator_include
from django.urls import re_path
from wagtail.admin import urls as wagtailadmin_urls
from wagtail.core import urls as wagtail_urls
from wagtail.documents import urls as wagtaildocs_urls

urlpatterns = [
    re_path(r"^cms/", decorator_include(csp_exempt, wagtailadmin_urls)),
    re_path(r"^documents/", decorator_include(csp_exempt, wagtaildocs_urls)),
    re_path(r"^infos/", decorator_include(csp_exempt, wagtail_urls)),
]
