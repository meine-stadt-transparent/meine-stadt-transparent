from django.shortcuts import redirect
from django.templatetags.static import static


def index(request, url):
    url = static('/elasticsearch/index.html') + '?url=' + url
    return redirect(url)
