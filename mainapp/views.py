from django.http import HttpResponse
from django.shortcuts import render
from django.template import loader

from mainapp.models.index.file import FileDocument


def index(request):
    template = loader.get_template('mainapp/index.html')
    context = {}
    return HttpResponse(template.render(context, request))


def search(request):
    template = loader.get_template('mainapp/search.html')
    context = {'results': []}

    if 'action' in request.POST:
        query = request.POST['query']
        s = FileDocument.search().filter("match", parsed_text=query)
        for hit in s:
            context['results'].append(hit.parsed_text)

    return HttpResponse(template.render(context, request))
