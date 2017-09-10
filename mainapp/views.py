from django.shortcuts import render

from mainapp.models.index.file import FileDocument


def index(request):
    return render(request, 'mainapp/index.html', {})


def search(request):
    context = {'results': []}

    if 'action' in request.POST:
        query = request.POST['query']
        s = FileDocument.search().filter("match", parsed_text=query)
        for hit in s:
            context['results'].append(hit.parsed_text)

    return render(request, 'mainapp/search.html', context)